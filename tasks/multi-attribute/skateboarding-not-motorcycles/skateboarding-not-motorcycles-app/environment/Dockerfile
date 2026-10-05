# syntax=docker/dockerfile:1.7
#
# ClubhouseAndSkate OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClubhouseAndSkate native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ClubhouseAndSkate writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClubhouseAndSkate app + its autostart launcher.
COPY clubhouseandskate.py /opt/clubhouseandskate/clubhouseandskate.py
COPY start-clubhouseandskate.sh /opt/clubhouseandskate/start-clubhouseandskate.sh
RUN chmod +x /opt/clubhouseandskate/start-clubhouseandskate.sh

WORKDIR /app
