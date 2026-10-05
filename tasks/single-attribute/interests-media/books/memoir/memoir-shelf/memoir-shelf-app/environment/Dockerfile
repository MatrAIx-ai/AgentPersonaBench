# syntax=docker/dockerfile:1.7
#
# ShelfMate OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ShelfMate native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Place holds", ShelfMate writes /app/output/holds.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ShelfMate app + its autostart launcher.
COPY shelfmate.py /opt/shelfmate/shelfmate.py
COPY start-shelfmate.sh /opt/shelfmate/start-shelfmate.sh
RUN chmod +x /opt/shelfmate/start-shelfmate.sh

WORKDIR /app
