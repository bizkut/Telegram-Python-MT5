import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events

from signal_interpreter import interpret_signal
from mt5_executor import initialize_mt5, execute_trade

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH")
# Split by comma if multiple IDs and convert to int
CHANNEL_IDS_ENV = os.getenv("TELEGRAM_CHANNEL_IDS", "")
CHANNEL_IDS = [int(x) for x in CHANNEL_IDS_ENV.split(",")] if CHANNEL_IDS_ENV else []

client = TelegramClient('anon', API_ID, API_HASH)

@client.on(events.NewMessage(chats=CHANNEL_IDS))
async def handler(event):
    message_text = event.message.message
    print(f"New Message Detected: {message_text[:100]}...")
    
    # Interpret
    signal_data = interpret_signal(message_text)
    print(f"Interpreted Signal: {signal_data}")
    
    if signal_data.get('is_signal'):
        # Execute Trade
        # Note: MT5 calls must be thread-safe. 
        # Since Telethon is async, and MT5 is synchronous blocking, we run it directly here safely 
        # as long as we don't have high concurrency overlapping on the same API instance.
        # For production, might want an executor queue.
        execute_trade(signal_data)

async def main():
    print("Initializing MT5...")
    if not initialize_mt5():
        print("MT5 Initialization Failed (Check Docker/Wine/Env). Skipping trade execution but listening.")
    
    print("Listening for Telegram messages...")
    await client.start()
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
