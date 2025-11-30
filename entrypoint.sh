#!/bin/bash
set -e

# Start Xvfb in the background
Xvfb :0 -screen 0 1024x768x16 &
XVFB_PID=$!
sleep 2

# Navigate to where MT5 might install or custom path if user mounted it?
# MT5 library handles download/install of terminal automatically if not present in custom path.
# However, inside Wine, it usually installs to AppData.

# Run the Telegram Listener using Wine's Python
echo "Starting Telegram Signal Server..."
wine python src/telegram_listener.py

# Cleanup Xvfb on exit
kill $XVFB_PID
