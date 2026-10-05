# syntax=docker/dockerfile:1.7
#
# DayPassApp OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DayPassApp native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book screenings", DayPassApp writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DayPassApp app + its autostart launcher.
COPY daypassapp.py /opt/daypassapp/daypassapp.py
COPY start-daypassapp.sh /opt/daypassapp/start-daypassapp.sh
RUN chmod +x /opt/daypassapp/start-daypassapp.sh

WORKDIR /app
