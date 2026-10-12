# syntax=docker/dockerfile:1.7
#
# WatchClub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WatchClub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book events", WatchClub writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WatchClub app + its autostart launcher.
COPY watchclub.py /opt/watchclub/watchclub.py
COPY start-watchclub.sh /opt/watchclub/start-watchclub.sh
RUN chmod +x /opt/watchclub/start-watchclub.sh

WORKDIR /app
