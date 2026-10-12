# syntax=docker/dockerfile:1.7
#
# ClubhouseAndRegatta OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClubhouseAndRegatta native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", ClubhouseAndRegatta writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClubhouseAndRegatta app + its autostart launcher.
COPY clubhouseandregatta.py /opt/clubhouseandregatta/clubhouseandregatta.py
COPY start-clubhouseandregatta.sh /opt/clubhouseandregatta/start-clubhouseandregatta.sh
RUN chmod +x /opt/clubhouseandregatta/start-clubhouseandregatta.sh

WORKDIR /app
