# Use a base image with Wine and Python installed
# One of the best options for MT5 is 'scottyhardy/docker-wine' or similar base images.
# However, to be precise, we need a Windows environment.
# We will use 'tobix/wine:stable' and manually install things, or start from a known MT5 base.
# A popular approach is using GMV's metatrader docker concepts, but here is a custom lightweight one.

FROM scottyhardy/docker-wine:latest

# Switch to root to install dependencies
USER root

# Install additional tools
RUN apt-get update && apt-get install -y \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Setup Wine environment
ENV WINEPREFIX=/home/wineuser/.wine
ENV WINEARCH=win64
ENV WINEDEBUG=-all
ENV DISPLAY=:0

# Create X11 socket directory
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix

# Download Python installer
RUN wget https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe -O /tmp/python_installer.exe

# Switch to wineuser for Wine operations
USER wineuser
WORKDIR /home/wineuser

# Initialize Wine and install Python
RUN Xvfb :0 -screen 0 1024x768x16 & \
    sleep 3 && \
    wine /tmp/python_installer.exe /quiet InstallAllUsers=0 PrependPath=1 TargetDir=C:\\Python310 && \
    wineserver -w

# Install required Python packages
RUN Xvfb :0 -screen 0 1024x768x16 & \
    sleep 3 && \
    wine C:\\Python310\\python.exe -m pip install --upgrade pip && \
    wine C:\\Python310\\python.exe -m pip install MetaTrader5 openai python-dotenv telethon && \
    wineserver -w

# Copy Source Code (switch back to root for file operations)
USER root
WORKDIR /app
COPY src/ /app/src/
COPY .env /app/.env
# Copy the session file if generated externally (important for Telethon auth)
COPY anon.session* /app/

# Startup Script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh && chown -R wineuser:wineuser /app

# Switch back to wineuser for runtime
USER wineuser

ENTRYPOINT ["/app/entrypoint.sh"]
