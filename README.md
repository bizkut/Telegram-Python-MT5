# MT5 Signal Server with Telegram & OpenAI

This server listens to Forex signals from Telegram, extracts structured data (using GPT-4o-mini), and executes trades on MetaTrader 5 via a Dockerized Wine environment.

## Logic Overview

1.  **Telegram Listener (`src/telegram_listener.py`)**: Uses Telethon to spy on messages from configured channels.
2.  **Signal Interpreter (`src/signal_interpreter.py`)**: Sends message text to OpenAI. It extracts Entry, SL, TP, and Actions (Open, Close, Set BE).
    *   *Logic*: "Close profit now" messages try to close deals for that symbol (or all if unspecified) *only if they are in profit*.
3.  **MT5 Executor (`src/mt5_executor.py`)**:
    *   Runs inside a Linux Docker container using **Wine** to simulate Windows.
    *   Uses the official `MetaTrader5` Python library (which requires Windows DLLs).
    *   Automatically handles Order Open, Partial Close (if specified), and Move SL to Breakeven.

## Setup Instructions

### 1. Prerequisites
*   Docker & Docker Compose
*   Telegram API Credentials (from https://my.telegram.org)
*   OpenAI API Key
*   MetaTrader 5 Account Details

### 2. Configuration
Edit `.env`:
```ini
TELEGRAM_API_ID=12345
TELEGRAM_API_HASH=abcdef...
TELEGRAM_CHANNEL_IDS=-10012345678, -10098765432 # Comma separated
OPENAI_API_KEY=sk-proj-...
MT5_LOGIN=123456
MT5_PASSWORD=secret
MT5_SERVER=MetaQuotes-Demo
```

### 3. Telegram Authentication (Critical)
Telethon requires an interactive login to generate a session file (`anon.session`). You must do this **before** building the container.

Run locally:
```bash
# Install dependencies temporarily
pip install telethon python-dotenv

# Run auth script
python src/auth_telegram.py
```
Follow the prompts (phone number, code). This will generate `anon.session`.

### 4. Build and Run
```bash
docker-compose up --build
```
This will:
1.  Download a Wine-based specific image.
2.  Install Windows Python 3.10 and MT5 dependencies.
3.  Start Xvfb (Virtual Display).
4.  Launch the listener.

### 5. Testing
A test script is included to verify OpenAI extraction logic without trading.
```bash
# (Locally)
python src/test_interpreter.py
```

## Troubleshooting
*   **"MetaTrader5 package not found"**: Ensure you are running inside the Docker container (which uses Wine). The package does NOT work on native Linux/Mac.
*   **Authorization Errors**: Re-run `src/auth_telegram.py` to refresh `anon.session`.
*   **Architecture**: If on Apple Silicon (M1/M2), you might need `platform: linux/amd64` in docker-compose, and emulation will be slow. The `tobix/wine` image is x86_64.
