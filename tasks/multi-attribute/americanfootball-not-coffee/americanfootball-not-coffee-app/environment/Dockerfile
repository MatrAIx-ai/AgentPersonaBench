# syntax=docker/dockerfile:1.7
#
# ClubhouseAndGridiron OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClubhouseAndGridiron native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", ClubhouseAndGridiron writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClubhouseAndGridiron app + its autostart launcher.
COPY clubhouseandgridiron.py /opt/clubhouseandgridiron/clubhouseandgridiron.py
COPY start-clubhouseandgridiron.sh /opt/clubhouseandgridiron/start-clubhouseandgridiron.sh
RUN chmod +x /opt/clubhouseandgridiron/start-clubhouseandgridiron.sh

WORKDIR /app
