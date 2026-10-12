# syntax=docker/dockerfile:1.7
#
# BankStart OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BankStart native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Pin tiles", BankStart writes /app/output/tiles.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BankStart app + its autostart launcher.
COPY bankstart.py /opt/bankstart/bankstart.py
COPY start-bankstart.sh /opt/bankstart/start-bankstart.sh
RUN chmod +x /opt/bankstart/start-bankstart.sh

WORKDIR /app
