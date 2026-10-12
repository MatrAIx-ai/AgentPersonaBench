# syntax=docker/dockerfile:1.7
#
# DaysAirfield OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DaysAirfield native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book days", DaysAirfield writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DaysAirfield app + its autostart launcher.
COPY daysairfield.py /opt/daysairfield/daysairfield.py
COPY start-daysairfield.sh /opt/daysairfield/start-daysairfield.sh
RUN chmod +x /opt/daysairfield/start-daysairfield.sh

WORKDIR /app
