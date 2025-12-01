#!/bin/bash
set -e

# Start Xvfb in the background
Xvfb :0 -screen 0 1024x768x16 &
XVFB_PID=$!
sleep 3

# Trap to cleanup Xvfb on exit
trap "kill $XVFB_PID 2>/dev/null" EXIT

# Run the Telegram Listener using Wine's Python
echo "Starting Telegram Signal Server..."
wine C:\\Python310\\python.exe src/telegram_listener.py
