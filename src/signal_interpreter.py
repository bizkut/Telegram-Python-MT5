import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are an expert Forex Signal Interpreter. Your job is to extract trading signals from Telegram messages and convert them into a strict JSON format.

Supported Actions:
- OPEN: Open a new trade (BUY/SELL)
- CLOSE: Close an existing trade
- MODIFY: Modify an existing trade (e.g., move SL to BE, or move SL to specific price)
- NONE: No trading signal detected

JSON Schema:
{
  "is_signal": boolean,
  "action": "OPEN" | "CLOSE" | "MODIFY" | "NONE",
  "sub_action": "BUY" | "SELL" | "CLOSE_FULL" | "CLOSE_HALF" | "SET_BE" | "SET_SL" | null,
  "symbol": string | null, (e.g. "XAUUSD")
  "entry": [float] | null, (List of entry prices, usually a range like 2000-2005)
  "sl": float | null,
  "tp": [float] | null, (List of Take Profit levels)
  "confidence": float, (0.0 to 1.0)
  "raw_message": string,
  "notes": string (Any specific conditions, e.g., "Close only if in profit")
}

Specific Logic:
- "Let’s CLOSE our profit now and set breakeven" -> This implies TWO actions usually, but often means "Secure profits". If the message allows holding, treat it as a management signal.
  - If "Close our profit now" -> Action: CLOSE, Sub_action: CLOSE_FULL (or HALF if specified).
  - if "Set breakeven" -> Action: MODIFY, Sub_action: SET_BE.
  - If both are present, prioritize proper extraction. You might need to handle this as a composite, but for now, output the primary intent. If it says "Close... and set breakeven if you wish to hold", it gives the user a choice. Map this to CLOSE_FULL effectively to be safe, or SET_BE if the user is holding.
  - For this system, we will treat "Close profit now" as a CLOSE_FULL signal to secure gains unless "Half" is explicitly mentioned.
- "XAUUSD SELL ENTRY 4196-4201" -> Action: OPEN, Sub_action: SELL, Entry: [4196, 4201].
- "Move SL to 3981" -> Action: MODIFY, Sub_action: SET_SL, sl: 3981.0.

Example Input 1:
"XAUUSD BUY ENTRY 2000-2005 SL 1995 TP 2010 TP 2020"
Example Output 1:
{
  "is_signal": true,
  "action": "OPEN",
  "sub_action": "BUY",
  "symbol": "XAUUSD",
  "entry": [2000, 2005],
  "sl": 1995.0,
  "tp": [2010.0, 2020.0],
  ...
}

Example Input 2:
"Let’s CLOSE our profit now and set breakeven if you wish to hold now"
Example Output 2:
{
  "is_signal": true,
  "action": "CLOSE",
  "sub_action": "CLOSE_FULL", 
  "notes": "User option to hold with BE, but system defaults to securing profit."
}
"""

def interpret_signal(message_text):
    """
    Parses a text message via OpenAI and returns a structural dict.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": message_text}
            ],
            response_format={"type": "json_object"},
            temperature=0.1
        )
        
        content = response.choices[0].message.content
        data = json.loads(content)
        return data

    except Exception as e:
        print(f"Error interpreting signal: {e}")
        return {"is_signal": False, "error": str(e)}

if __name__ == "__main__":
    # Simple test
    sample_text = "XAUUSD SELL ENTRY 4196-4201 SL 4203 TP 4194 TP 4192 TP 4189"
    print(json.dumps(interpret_signal(sample_text), indent=2))
