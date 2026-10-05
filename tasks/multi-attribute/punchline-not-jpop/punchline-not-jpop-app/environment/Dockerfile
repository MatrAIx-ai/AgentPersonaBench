# syntax=docker/dockerfile:1.7
#
# AmpAndMic OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the AmpAndMic native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", AmpAndMic writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The AmpAndMic app + its autostart launcher.
COPY ampandmic.py /opt/ampandmic/ampandmic.py
COPY start-ampandmic.sh /opt/ampandmic/start-ampandmic.sh
RUN chmod +x /opt/ampandmic/start-ampandmic.sh

WORKDIR /app
