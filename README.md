# MT5 Signal Server with Telegram & OpenAI

Listens to Forex signals from Telegram, interprets them with GPT-4o-mini, and executes trades on MetaTrader 5.

**Windows only** - MetaTrader5 Python library requires Windows.

## Quick Start

### Option 1: Run from Source
```bash
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your credentials
python main.py
```

### Option 2: Build Executable
```bash
build.bat
# Copy .env and anon.session to dist/ folder
dist\MT5SignalServer.exe
```

## Configuration

Copy `.env.example` to `.env`:
```ini
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=abcdef...
TELEGRAM_CHANNEL_IDS=-10012345678,-10098765432
OPENAI_API_KEY=sk-proj-...
MT5_LOGIN=123456
MT5_PASSWORD=secret
MT5_SERVER=MetaQuotes-Demo
LOT_SIZE=0.01
```

## First Run - Telegram Auth

On first run, you'll be prompted to authenticate with Telegram (phone + code). This creates `anon.session` - keep this file alongside the executable.

## Requirements

- Windows OS
- Python 3.10+ (for building)
- MetaTrader 5 terminal running
- Telegram API credentials (https://my.telegram.org)
- OpenAI API key

## How It Works

1. Monitors configured Telegram channels
2. Sends messages to GPT-4o-mini for signal extraction
3. Executes trades: OPEN (BUY/SELL), CLOSE, MODIFY (SL/BE)
4. Only closes positions that are in profit

## Troubleshooting

- **MT5 not connecting**: Ensure MT5 terminal is running and logged in
- **Telegram auth issues**: Delete `anon.session` and re-authenticate
