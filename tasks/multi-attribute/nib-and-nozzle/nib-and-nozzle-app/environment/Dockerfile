# syntax=docker/dockerfile:1.7
#
# StationPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StationPass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book passes", StationPass writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StationPass app + its autostart launcher.
COPY stationpass.py /opt/stationpass/stationpass.py
COPY start-stationpass.sh /opt/stationpass/start-stationpass.sh
RUN chmod +x /opt/stationpass/start-stationpass.sh

WORKDIR /app
