# syntax=docker/dockerfile:1.7
#
# ShelfApp OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ShelfApp native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Borrow loans", ShelfApp writes /app/output/loans.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ShelfApp app + its autostart launcher.
COPY shelfapp.py /opt/shelfapp/shelfapp.py
COPY start-shelfapp.sh /opt/shelfapp/start-shelfapp.sh
RUN chmod +x /opt/shelfapp/start-shelfapp.sh

WORKDIR /app
