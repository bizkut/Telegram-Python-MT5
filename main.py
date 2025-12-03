import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from openai import OpenAI
from telethon import TelegramClient, events
import MetaTrader5 as mt5

# Load environment variables
if getattr(sys, 'frozen', False):
    # Running as compiled exe
    base_path = os.path.dirname(sys.executable)
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

env_path = os.path.join(base_path, '.env')
load_dotenv(env_path)

# Configuration
TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")
CHANNEL_IDS_ENV = os.getenv("TELEGRAM_CHANNEL_IDS", "")
CHANNEL_IDS = [int(x.strip()) for x in CHANNEL_IDS_ENV.split(",") if x.strip()]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

MT5_LOGIN = int(os.getenv("MT5_LOGIN", 0))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
LOT_SIZE = float(os.getenv("LOT_SIZE", 0.01))
DEVIATION = 20

# OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

SIGNAL_PROMPT = """You are an expert Forex Signal Interpreter. Extract trading signals from Telegram messages into JSON.

Actions: OPEN, CLOSE, MODIFY, NONE
Sub-actions: BUY, SELL, CLOSE_FULL, CLOSE_HALF, SET_BE, SET_SL

JSON Schema:
{
  "is_signal": boolean,
  "action": "OPEN" | "CLOSE" | "MODIFY" | "NONE",
  "sub_action": "BUY" | "SELL" | "CLOSE_FULL" | "CLOSE_HALF" | "SET_BE" | "SET_SL" | null,
  "symbol": string | null,
  "entry": [float] | null,
  "sl": float | null,
  "tp": [float] | null,
  "confidence": float,
  "notes": string
}

Rules:
- "XAUUSD SELL ENTRY 4196-4201" -> OPEN, SELL, entry: [4196, 4201]
- "Close profit now" -> CLOSE, CLOSE_FULL
- "Move SL to 3981" -> MODIFY, SET_SL, sl: 3981
- "Set breakeven" -> MODIFY, SET_BE"""


def interpret_signal(message_text: str) -> dict:
    """Parse message via OpenAI and return structured signal."""
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SIGNAL_PROMPT},
                {"role": "user", "content": message_text}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[ERROR] Signal interpretation failed: {e}")
        return {"is_signal": False, "error": str(e)}


def init_mt5() -> bool:
    """Initialize and login to MT5."""
    if not mt5.initialize():
        print(f"[ERROR] MT5 initialize failed: {mt5.last_error()}")
        return False
    
    if mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER):
        print(f"[OK] Connected to MT5 account #{MT5_LOGIN}")
        return True
    
    print(f"[ERROR] MT5 login failed: {mt5.last_error()}")
    return False


def execute_trade(signal: dict):
    """Execute trade based on signal."""
    if not signal.get('is_signal'):
        return

    action = signal.get('action')
    symbol = signal.get('symbol')

    if symbol:
        info = mt5.symbol_info(symbol)
        if info is None:
            print(f"[ERROR] Symbol {symbol} not found")
            return
        if not info.visible and not mt5.symbol_select(symbol, True):
            print(f"[ERROR] Cannot select symbol {symbol}")
            return

    if action == "OPEN":
        _open_position(signal)
    elif action == "CLOSE":
        _close_position(signal)
    elif action == "MODIFY":
        _modify_position(signal)


def _get_filling_mode(symbol: str):
    """Get the appropriate filling mode for a symbol."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return mt5.ORDER_FILLING_RETURN
    
    filling_mode = info.filling_mode
    if filling_mode & 1:  # SYMBOL_FILLING_FOK
        return mt5.ORDER_FILLING_FOK
    elif filling_mode & 2:  # SYMBOL_FILLING_IOC
        return mt5.ORDER_FILLING_IOC
    else:
        return mt5.ORDER_FILLING_RETURN


def _open_position(signal: dict):
    symbol = signal['symbol']
    sub_action = signal.get('sub_action')
    
    order_type = mt5.ORDER_TYPE_BUY if sub_action == "BUY" else mt5.ORDER_TYPE_SELL
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print(f"[ERROR] Failed to get tick data for {symbol}")
        return
    
    price = tick.ask if sub_action == "BUY" else tick.bid
    
    sl = float(signal.get('sl') or 0)
    tp_list = signal.get('tp') or []
    tp = float(tp_list[0]) if tp_list else 0
    
    filling_mode = _get_filling_mode(symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": LOT_SIZE,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": DEVIATION,
        "magic": 234000,
        "comment": "TG Signal",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_mode,
    }
    
    result = mt5.order_send(request)
    if result is None:
        print(f"[ERROR] order_send failed, error: {mt5.last_error()}")
        return
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"[ERROR] Open {sub_action} {symbol} failed, retcode={result.retcode}, comment={result.comment}")
        result_dict = result._asdict()
        for field in result_dict.keys():
            print(f"   {field}={result_dict[field]}")
    else:
        print(f"[OK] Opened {sub_action} {symbol}: ticket={result.order}, price={result.price}, volume={result.volume}")


def _close_position(signal: dict):
    positions = mt5.positions_get()
    if not positions:
        print("[INFO] No open positions to close")
        return

    sub_action = signal.get('sub_action')
    target_symbol = signal.get('symbol')

    for pos in positions:
        if target_symbol and pos.symbol != target_symbol:
            continue
        if pos.profit <= 0:
            print(f"[SKIP] {pos.ticket} not in profit ({pos.profit})")
            continue

        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            print(f"[ERROR] Failed to get tick data for {pos.symbol}")
            continue
            
        price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        
        volume = pos.volume
        if sub_action == "CLOSE_HALF":
            volume = max(round(pos.volume / 2, 2), 0.01)

        filling_mode = _get_filling_mode(pos.symbol)
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": volume,
            "type": close_type,
            "position": pos.ticket,
            "price": price,
            "deviation": DEVIATION,
            "magic": 234000,
            "comment": "TG Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }
        
        result = mt5.order_send(request)
        if result is None:
            print(f"[ERROR] Close order_send failed, error: {mt5.last_error()}")
            continue
            
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[ERROR] Close {pos.symbol} failed, retcode={result.retcode}, comment={result.comment}")
        else:
            print(f"[OK] Closed {pos.symbol}: ticket={pos.ticket}, volume={volume}")


def _modify_position(signal: dict):
    sub_action = signal.get('sub_action')
    if sub_action not in ["SET_BE", "SET_SL"]:
        return

    positions = mt5.positions_get()
    if not positions:
        print("[INFO] No open positions to modify")
        return

    target_symbol = signal.get('symbol')
    new_sl_value = signal.get('sl')

    for pos in positions:
        if target_symbol and pos.symbol != target_symbol:
            continue

        new_sl = pos.sl

        if sub_action == "SET_BE":
            if pos.type == mt5.ORDER_TYPE_BUY and pos.price_current > pos.price_open:
                new_sl = pos.price_open
            elif pos.type == mt5.ORDER_TYPE_SELL and pos.price_current < pos.price_open:
                new_sl = pos.price_open
            else:
                continue
        elif sub_action == "SET_SL" and new_sl_value:
            new_sl = float(new_sl_value)

        if abs(new_sl - pos.sl) < 0.00001:
            continue

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "sl": new_sl,
            "tp": pos.tp,
            "magic": 234000,
            "comment": "TG Modify"
        }
        
        result = mt5.order_send(request)
        if result is None:
            print(f"[ERROR] Modify order_send failed, error: {mt5.last_error()}")
            continue
            
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"[ERROR] Modify SL {pos.symbol} failed, retcode={result.retcode}, comment={result.comment}")
        else:
            print(f"[OK] Modified SL {pos.symbol}: ticket={pos.ticket}, new_sl={new_sl}")


# Telegram client
session_path = os.path.join(base_path, 'anon')
telegram_client = TelegramClient(session_path, TELEGRAM_API_ID, TELEGRAM_API_HASH)


@telegram_client.on(events.NewMessage(chats=CHANNEL_IDS))
async def on_message(event):
    text = event.message.message
    print(f"\n[MSG] {text[:100]}...")
    
    signal = interpret_signal(text)
    print(f"[SIGNAL] {signal}")
    
    if signal.get('is_signal'):
        execute_trade(signal)


async def main():
    print("=" * 50)
    print("MT5 Telegram Signal Server")
    print("=" * 50)
    
    if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
        print("[ERROR] Missing Telegram credentials in .env")
        return
    
    if not OPENAI_API_KEY:
        print("[ERROR] Missing OPENAI_API_KEY in .env")
        return
    
    print(f"[CONFIG] Monitoring {len(CHANNEL_IDS)} channel(s)")
    print(f"[CONFIG] Lot size: {LOT_SIZE}")
    
    print("\n[INIT] Connecting to MT5...")
    if not init_mt5():
        print("[WARN] MT5 not available - signals will be logged but not executed")
    
    print("[INIT] Connecting to Telegram...")
    await telegram_client.start()
    print("[OK] Listening for signals... (Ctrl+C to stop)\n")
    
    await telegram_client.run_until_disconnected()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[EXIT] Shutting down...")
        mt5.shutdown()
