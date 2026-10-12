# syntax=docker/dockerfile:1.7
#
# LunchCard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LunchCard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Place pre-order", LunchCard writes /app/output/preorder.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LunchCard app + its autostart launcher.
COPY lunchcard.py /opt/lunchcard/lunchcard.py
COPY start-lunchcard.sh /opt/lunchcard/start-lunchcard.sh
RUN chmod +x /opt/lunchcard/start-lunchcard.sh

WORKDIR /app
