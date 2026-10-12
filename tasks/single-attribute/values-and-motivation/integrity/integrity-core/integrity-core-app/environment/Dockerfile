# syntax=docker/dockerfile:1.7
#
# Compass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Compass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Compass writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Compass app + its autostart launcher.
COPY compass.py /opt/compass/compass.py
COPY start-compass.sh /opt/compass/start-compass.sh
RUN chmod +x /opt/compass/start-compass.sh

WORKDIR /app
