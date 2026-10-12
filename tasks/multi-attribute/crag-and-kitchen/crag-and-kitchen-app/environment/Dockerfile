# syntax=docker/dockerfile:1.7
#
# PeakPlanner OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PeakPlanner native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book packages", PeakPlanner writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PeakPlanner app + its autostart launcher.
COPY peakplanner.py /opt/peakplanner/peakplanner.py
COPY start-peakplanner.sh /opt/peakplanner/start-peakplanner.sh
RUN chmod +x /opt/peakplanner/start-peakplanner.sh

WORKDIR /app
