# Use a base image with Wine and Python installed
# One of the best options for MT5 is 'scottyhardy/docker-wine' or similar base images.
# However, to be precise, we need a Windows environment.
# We will use 'tobix/wine:stable' and manually install things, or start from a known MT5 base.
# A popular approach is using GMV's metatrader docker concepts, but here is a custom lightweight one.

FROM tobix/wine:stable

# Switch to root to install dependencies
USER root

# Install Xvfb (Virtual Display), winbind, and python build tools
RUN apt-get update && apt-get install -y \
    xvfb \
    winbind \
    cabextract \
    wget \
    gnupg2 \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Setup Wine environment
ENV WINEPREFIX=/root/.wine
ENV WINEARCH=win64
ENV WINEDEBUG=-all

# Initialize Wine
RUN winecfg || true

# Install Python for Windows
# Downloading Python 3.10 for Windows (AMD64)
RUN wget https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe -O python_installer.exe

# Silent install of Python
# Prepend with xvfb-run to simulate a display if installer needs it (usually silent doesn't)
RUN xvfb-run wine python_installer.exe /quiet InstallAllUsers=1 PrependPath=1

# Wait for installation to settle
RUN sleep 5

# Install required Python packages via pip (running inside Wine's Python)
# We need to explicitly call python from wine
RUN wine python -m pip install --upgrade pip
RUN wine python -m pip install MetaTrader5 openai python-dotenv telethon

# Copy Source Code
WORKDIR /app
COPY src/ /app/src/
COPY .env /app/.env
# Copy the session file if generated externally (important for Telethon auth)
COPY anon.session* /app/

# Environment Variables for Display
ENV DISPLAY=:0

# Startup Script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
