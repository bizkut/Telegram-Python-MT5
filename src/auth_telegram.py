import os
from dotenv import load_dotenv
from telethon import TelegramClient

load_dotenv()

API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
API_HASH = os.getenv("TELEGRAM_API_HASH")

def auth():
    if not API_ID or not API_HASH:
        print("Please set TELEGRAM_API_ID and TELEGRAM_API_HASH in .env file first.")
        return

    print("Connecting to Telegram to generate session file...")
    client = TelegramClient('anon', API_ID, API_HASH)
    
    async def main():
        await client.start()
        print("Successfully authenticated! 'anon.session' file created.")
        print("You can now build the Docker container.")
    
    client.loop.run_until_complete(main())

if __name__ == '__main__':
    auth()
