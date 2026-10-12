# syntax=docker/dockerfile:1.7
#
# HarbourApp OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HarbourApp native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book slots", HarbourApp writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HarbourApp app + its autostart launcher.
COPY harbourapp.py /opt/harbourapp/harbourapp.py
COPY start-harbourapp.sh /opt/harbourapp/start-harbourapp.sh
RUN chmod +x /opt/harbourapp/start-harbourapp.sh

WORKDIR /app
