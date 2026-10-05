# syntax=docker/dockerfile:1.7
#
# DaysTrip OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DaysTrip native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book packages", DaysTrip writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DaysTrip app + its autostart launcher.
COPY daystrip.py /opt/daystrip/daystrip.py
COPY start-daystrip.sh /opt/daystrip/start-daystrip.sh
RUN chmod +x /opt/daystrip/start-daystrip.sh

WORKDIR /app
