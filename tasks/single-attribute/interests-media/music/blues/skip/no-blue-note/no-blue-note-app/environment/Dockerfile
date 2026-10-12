# syntax=docker/dockerfile:1.7
#
# BandPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BandPass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve slots", BandPass writes /app/output/reservations.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BandPass app + its autostart launcher.
COPY bandpass.py /opt/bandpass/bandpass.py
COPY start-bandpass.sh /opt/bandpass/start-bandpass.sh
RUN chmod +x /opt/bandpass/start-bandpass.sh

WORKDIR /app
