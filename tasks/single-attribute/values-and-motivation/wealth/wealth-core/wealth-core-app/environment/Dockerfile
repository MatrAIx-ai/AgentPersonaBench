# syntax=docker/dockerfile:1.7
#
# NextMove OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NextMove native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, NextMove writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NextMove app + its autostart launcher.
COPY nextmove.py /opt/nextmove/nextmove.py
COPY start-nextmove.sh /opt/nextmove/start-nextmove.sh
RUN chmod +x /opt/nextmove/start-nextmove.sh

WORKDIR /app
