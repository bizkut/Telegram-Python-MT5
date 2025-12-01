@echo off
echo Building MT5 Signal Server...
echo.

pip install -r requirements.txt

pyinstaller --onefile --name MT5SignalServer --icon=NONE --add-data ".env.example;." main.py

echo.
echo Build complete! Executable is in dist\MT5SignalServer.exe
echo.
echo IMPORTANT: Copy your .env file to the same folder as MT5SignalServer.exe
pause
