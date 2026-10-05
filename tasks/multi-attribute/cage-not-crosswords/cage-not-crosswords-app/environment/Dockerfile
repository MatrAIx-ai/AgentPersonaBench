# syntax=docker/dockerfile:1.7
#
# CentreMidweek OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CentreMidweek native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Wednesdays", CentreMidweek writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CentreMidweek app + its autostart launcher.
COPY centremidweek.py /opt/centremidweek/centremidweek.py
COPY start-centremidweek.sh /opt/centremidweek/start-centremidweek.sh
RUN chmod +x /opt/centremidweek/start-centremidweek.sh

WORKDIR /app
