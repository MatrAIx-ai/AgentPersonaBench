# syntax=docker/dockerfile:1.7
#
# StayPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StayPass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book passes", StayPass writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StayPass app + its autostart launcher.
COPY staypass.py /opt/staypass/staypass.py
COPY start-staypass.sh /opt/staypass/start-staypass.sh
RUN chmod +x /opt/staypass/start-staypass.sh

WORKDIR /app
