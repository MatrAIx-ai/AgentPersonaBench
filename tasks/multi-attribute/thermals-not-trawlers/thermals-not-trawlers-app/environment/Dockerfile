# syntax=docker/dockerfile:1.7
#
# DaysCoast OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DaysCoast native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book packages", DaysCoast writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DaysCoast app + its autostart launcher.
COPY dayscoast.py /opt/dayscoast/dayscoast.py
COPY start-dayscoast.sh /opt/dayscoast/start-dayscoast.sh
RUN chmod +x /opt/dayscoast/start-dayscoast.sh

WORKDIR /app
