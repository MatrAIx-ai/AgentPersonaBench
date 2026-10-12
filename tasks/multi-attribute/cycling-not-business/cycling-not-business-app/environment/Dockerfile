# syntax=docker/dockerfile:1.7
#
# SundaysRaceAndTalk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SundaysRaceAndTalk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SundaysRaceAndTalk writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SundaysRaceAndTalk app + its autostart launcher.
COPY sundaysraceandtalk.py /opt/sundaysraceandtalk/sundaysraceandtalk.py
COPY start-sundaysraceandtalk.sh /opt/sundaysraceandtalk/start-sundaysraceandtalk.sh
RUN chmod +x /opt/sundaysraceandtalk/start-sundaysraceandtalk.sh

WORKDIR /app
