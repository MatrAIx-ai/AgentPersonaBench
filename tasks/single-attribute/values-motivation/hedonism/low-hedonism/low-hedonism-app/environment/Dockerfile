# syntax=docker/dockerfile:1.7
#
# StayPerk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StayPerk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Choose perks", StayPerk writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StayPerk app + its autostart launcher.
COPY stayperk.py /opt/stayperk/stayperk.py
COPY start-stayperk.sh /opt/stayperk/start-stayperk.sh
RUN chmod +x /opt/stayperk/start-stayperk.sh

WORKDIR /app
