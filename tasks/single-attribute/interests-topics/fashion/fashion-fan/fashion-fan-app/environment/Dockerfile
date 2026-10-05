# syntax=docker/dockerfile:1.7
#
# KioskDigest OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE +
# xdotool + scrot) PLUS Python Tkinter and the KioskDigest native GUI app
# baked in. The CUA agent (persona-computer-1) drives it by screenshot +
# coordinate click; on confirm the app writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/fashionfan/app.py
COPY start-app.sh /opt/fashionfan/start-app.sh
RUN chmod +x /opt/fashionfan/start-app.sh

WORKDIR /app
