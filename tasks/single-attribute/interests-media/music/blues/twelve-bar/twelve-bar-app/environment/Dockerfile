# syntax=docker/dockerfile:1.7
#
# FestBand OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FestBand native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve slots", FestBand writes /app/output/reservations.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FestBand app + its autostart launcher.
COPY festband.py /opt/festband/festband.py
COPY start-festband.sh /opt/festband/start-festband.sh
RUN chmod +x /opt/festband/start-festband.sh

WORKDIR /app
