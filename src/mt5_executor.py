import os
import MetaTrader5 as mt5
from dotenv import load_dotenv

load_dotenv()

LOGIN = int(os.getenv("MT5_LOGIN", 0))
PASSWORD = os.getenv("MT5_PASSWORD")
SERVER = os.getenv("MT5_SERVER")

# Use a default lot size or calculate dynamically later
LOT_SIZE = 0.01  
DEVIATION = 20

def initialize_mt5():
    """Initializes and logs into MT5."""
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return False
    
    authorized = mt5.login(LOGIN, password=PASSWORD, server=SERVER)
    if authorized:
        print(f"Connected to MT5 account #{LOGIN}")
    else:
        print("failed to connect at account #{}, error code: {}".format(LOGIN, mt5.last_error()))
    return authorized

def execute_trade(signal):
    """
    Executes a trade based on the JSON signal structure.
    signal = {
      "action": "OPEN" | "CLOSE" | "MODIFY",
      "sub_action": "BUY" | "SELL" | ...,
      "symbol": "XAUUSD",
      "entry": [...],
      "sl": float,
      "tp": [float]
    }
    """
    if not signal.get('is_signal'):
        return

    action = signal.get('action')
    symbol = signal.get('symbol')

    # Ensure symbol is selected
    if symbol:
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            print(f"{symbol} not found, can not check orders")
            return
        if not symbol_info.visible:
            print(f"{symbol} is not visible, trying to switch on")
            if not mt5.symbol_select(symbol, True):
                print(f"symbol_select({symbol}) failed, exit")
                return

    if action == "OPEN":
        _open_position(signal)
    elif action == "CLOSE":
        _close_position(signal)
    elif action == "MODIFY":
        _modify_position(signal)

def _open_position(signal):
    symbol = signal['symbol']
    lot = LOT_SIZE
    sub_action = signal.get('sub_action')
    
    # Check current price vs entry range?
    # For now, we assume 'Instant execution' or simple limit if price is far.
    # To keep things robust, we'll try MARKET execution first if within range.
    
    order_type = mt5.ORDER_TYPE_BUY if sub_action == "BUY" else mt5.ORDER_TYPE_SELL
    price = mt5.symbol_info_tick(symbol).ask if sub_action == "BUY" else mt5.symbol_info_tick(symbol).bid
    
    # Calculate SL/TP
    sl = float(signal.get('sl', 0.0))
    tp_list = signal.get('tp', [])
    tp = float(tp_list[0]) if tp_list else 0.0 # Take first TP for simplicity or create multiple orders
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": DEVIATION,
        "magic": 234000,
        "comment": "OpenAI Signal",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    
    result = mt5.order_send(request)
    print(f"Order Send Result: {result}")
    
    # If using multiple TPs, we could open multiple partial positions here.

def _close_position(signal):
    """
    Closes positions.
    logic: "Close only if in profit" if noted in notes?
    The prompt says: "The decision should make sure that we are in profit."
    """
    # symbol = signal.get('symbol') # Symbol might be null in generic "Close All" messages, but Telegram usually implies the context position. 
    # Current limitation: We need to know WHICH symbol.
    # We will iterate all open positions and if they match the 'recent' signal context (or all for simplest approach).
    
    positions = mt5.positions_get()
    if positions is None:
        return

    sub_action = signal.get('sub_action')
    # Use context symbol if available, else assume we might need to close EVERYTHING? 
    # Usually signals carry the symbol or reply to it. We'll assume symbol is provided or inferred.
    # If symbol is missing in JSON, we can't safely close.
    target_symbol = signal.get('symbol') 

    for pos in positions:
        # Filter by symbol if provided
        if target_symbol and pos.symbol != target_symbol:
            continue
            
        # Check Profit Condition
        if pos.profit <= 0:
            print(f"Skipping trade {pos.ticket} ({pos.symbol}) - Not in profit ({pos.profit})")
            continue
            
        # Execute Close
        # Trade Type inverse
        type_dict = {mt5.ORDER_TYPE_BUY: mt5.ORDER_TYPE_SELL, mt5.ORDER_TYPE_SELL: mt5.ORDER_TYPE_BUY}
        price_dict = {mt5.ORDER_TYPE_BUY: mt5.symbol_info_tick(pos.symbol).bid, mt5.ORDER_TYPE_SELL: mt5.symbol_info_tick(pos.symbol).ask}
        
        volume = pos.volume
        if sub_action == "CLOSE_HALF":
            volume = round(pos.volume / 2, 2)
            if volume < 0.01: volume = 0.01 # Min lot
            
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": volume,
            "type": type_dict[pos.type],
            "position": pos.ticket,
            "price": price_dict[pos.type],
            "deviation": DEVIATION,
            "magic": 234000,
            "comment": "Signal Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        print(f"Close Result: {result}")

def _modify_position(signal):
    """
    Handles modification requests (Set BE, Set SL).
    """
    sub_action = signal.get('sub_action')
    if sub_action not in ["SET_BE", "SET_SL"]:
        return

    positions = mt5.positions_get()
    target_symbol = signal.get('symbol') 

    new_requested_sl = signal.get('sl')

    for pos in positions:
        if target_symbol and pos.symbol != target_symbol:
            continue
        
        new_sl = pos.sl

        if sub_action == "SET_BE":
            # Break Even means moving SL to Open Price
            # Only if current price allows (in profit)
            if pos.type == mt5.ORDER_TYPE_BUY:
                if pos.price_open >= pos.price_current: continue # Losing trade
                new_sl = pos.price_open
            else:
                if pos.price_open <= pos.price_current: continue # Losing trade
                new_sl = pos.price_open
        
        elif sub_action == "SET_SL":
            if new_requested_sl is None: continue
            new_sl = float(new_requested_sl)

        # Skip if SL hasn't changed to avoid errors
        if abs(new_sl - pos.sl) < 0.00001:
            continue

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "sl": new_sl,
            "tp": pos.tp,
            "magic": 234000,
            "comment": "Modify SL"
        }
        
        result = mt5.order_send(request)
        print(f"Modify Result: {result}")
