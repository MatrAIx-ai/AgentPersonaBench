# syntax=docker/dockerfile:1.7
#
# SpineAndSky OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SpineAndSky native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book meetups", SpineAndSky writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SpineAndSky app + its autostart launcher.
COPY spineandsky.py /opt/spineandsky/spineandsky.py
COPY start-spineandsky.sh /opt/spineandsky/start-spineandsky.sh
RUN chmod +x /opt/spineandsky/start-spineandsky.sh

WORKDIR /app
