# syntax=docker/dockerfile:1.7
#
# WatchList OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WatchList native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Lock picks", WatchList writes /app/output/picks.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WatchList app + its autostart launcher.
COPY watchlist.py /opt/watchlist/watchlist.py
COPY start-watchlist.sh /opt/watchlist/start-watchlist.sh
RUN chmod +x /opt/watchlist/start-watchlist.sh

WORKDIR /app
