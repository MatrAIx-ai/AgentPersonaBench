# syntax=docker/dockerfile:1.7
#
# CityCard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CityCard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve entries", CityCard writes /app/output/entries.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CityCard app + its autostart launcher.
COPY citycard.py /opt/citycard/citycard.py
COPY start-citycard.sh /opt/citycard/start-citycard.sh
RUN chmod +x /opt/citycard/start-citycard.sh

WORKDIR /app
