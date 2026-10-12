# syntax=docker/dockerfile:1.7
#
# ConcertAndTalk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ConcertAndTalk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ConcertAndTalk writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ConcertAndTalk app + its autostart launcher.
COPY concertandtalk.py /opt/concertandtalk/concertandtalk.py
COPY start-concertandtalk.sh /opt/concertandtalk/start-concertandtalk.sh
RUN chmod +x /opt/concertandtalk/start-concertandtalk.sh

WORKDIR /app
