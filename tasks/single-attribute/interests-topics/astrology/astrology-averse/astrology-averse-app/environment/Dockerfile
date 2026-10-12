# syntax=docker/dockerfile:1.7
#
# MorningFeed OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE +
# xdotool + scrot) PLUS Python Tkinter and the MorningFeed native GUI app
# baked in. The CUA agent (persona-computer-1) drives it by screenshot +
# coordinate click; on confirm the app writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/astrologyaverse/app.py
COPY start-app.sh /opt/astrologyaverse/start-app.sh
RUN chmod +x /opt/astrologyaverse/start-app.sh

WORKDIR /app
