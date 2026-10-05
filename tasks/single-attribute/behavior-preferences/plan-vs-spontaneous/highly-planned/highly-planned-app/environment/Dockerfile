# syntax=docker/dockerfile:1.7
#
# TripDeck OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TripDeck native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, TripDeck writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TripDeck app + its autostart launcher.
COPY tripdeck.py /opt/tripdeck/tripdeck.py
COPY start-tripdeck.sh /opt/tripdeck/start-tripdeck.sh
RUN chmod +x /opt/tripdeck/start-tripdeck.sh

WORKDIR /app
