# syntax=docker/dockerfile:1.7
#
# ClubhouseAndTrack OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClubhouseAndTrack native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ClubhouseAndTrack writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClubhouseAndTrack app + its autostart launcher.
COPY clubhouseandtrack.py /opt/clubhouseandtrack/clubhouseandtrack.py
COPY start-clubhouseandtrack.sh /opt/clubhouseandtrack/start-clubhouseandtrack.sh
RUN chmod +x /opt/clubhouseandtrack/start-clubhouseandtrack.sh

WORKDIR /app
