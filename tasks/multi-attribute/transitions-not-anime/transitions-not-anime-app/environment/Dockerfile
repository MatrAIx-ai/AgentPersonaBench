# syntax=docker/dockerfile:1.7
#
# CentreBundlesSunday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CentreBundlesSunday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", CentreBundlesSunday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CentreBundlesSunday app + its autostart launcher.
COPY centrebundlessunday.py /opt/centrebundlessunday/centrebundlessunday.py
COPY start-centrebundlessunday.sh /opt/centrebundlessunday/start-centrebundlessunday.sh
RUN chmod +x /opt/centrebundlessunday/start-centrebundlessunday.sh

WORKDIR /app
