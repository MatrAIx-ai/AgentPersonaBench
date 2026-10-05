# syntax=docker/dockerfile:1.7
#
# CentreNight OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CentreNight native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Claim tickets", CentreNight writes /app/output/tickets.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CentreNight app + its autostart launcher.
COPY centrenight.py /opt/centrenight/centrenight.py
COPY start-centrenight.sh /opt/centrenight/start-centrenight.sh
RUN chmod +x /opt/centrenight/start-centrenight.sh

WORKDIR /app
