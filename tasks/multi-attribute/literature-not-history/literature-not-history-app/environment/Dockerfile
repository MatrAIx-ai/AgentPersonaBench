# syntax=docker/dockerfile:1.7
#
# SundaysReadingRoom OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SundaysReadingRoom native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SundaysReadingRoom writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SundaysReadingRoom app + its autostart launcher.
COPY sundaysreadingroom.py /opt/sundaysreadingroom/sundaysreadingroom.py
COPY start-sundaysreadingroom.sh /opt/sundaysreadingroom/start-sundaysreadingroom.sh
RUN chmod +x /opt/sundaysreadingroom/start-sundaysreadingroom.sh

WORKDIR /app
