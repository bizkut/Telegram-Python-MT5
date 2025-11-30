import json
from signal_interpreter import interpret_signal

def run_tests():
    sample_messages = [
        # --- Original Samples ---
        """And 130pips we GOOO✅""",
        
        """Let’s CLOSE our profit now and set breakeven if you wish to hold now‼️
        Nonstop smashing TP with Snipers🫡""",
        
        """Let's scalping sell gold slowly
        XAUUSD SELL 
        ENTRY 4196-4201
        SL 4203
        TP 4194
        TP 4192
        TP 4189
        👉GOLD SNIPERS VIP""",
        
        # --- NEW Samples (Complex) ---
        
        """Round 3 STRAIGHT TO TP1//30pips✅

        Let’s CLOSE our profit now and set breakeven if you wish to hold now‼️
        
        We focus on scalping traders🔥🔥🔥""",
        
        """I’ll move my SL to 3981 temporarily""",
        
        """‼️400pips trade coming here! 
        Join fast:👉 t.me/+kpDe_PXbkbZiOTE0""",
        
        """Let's scalping buy gold slowly
        XAUUSD BUY 
        ENTRY 4021-4014
        SL 4013
        TP 4024
        TP 4027
        TP 4028
        👉GOLD SNIPERS VIP""",
        
        """ANDDD TP1//53pips✅
        CLOSE our profit now‼️
        Let's be smart. 
        If you plan to keep chasing, secure your gains and trail your SL to the entry price.🙌"""
    ]

    for i, msg in enumerate(sample_messages):
        print(f"--- Message {i+1} ---")
        truncated = msg.strip().replace('\n', ' ')[:60]
        print(f"Input: {truncated}...")
        data = interpret_signal(msg)
        print("Output:")
        print(json.dumps(data, indent=2))
        print("\n")

if __name__ == "__main__":
    run_tests()
