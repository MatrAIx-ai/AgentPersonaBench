# syntax=docker/dockerfile:1.7
#
# PanRack OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PanRack native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Take these", PanRack writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PanRack app + its autostart launcher.
COPY panrack.py /opt/panrack/panrack.py
COPY start-panrack.sh /opt/panrack/start-panrack.sh
RUN chmod +x /opt/panrack/start-panrack.sh

WORKDIR /app
