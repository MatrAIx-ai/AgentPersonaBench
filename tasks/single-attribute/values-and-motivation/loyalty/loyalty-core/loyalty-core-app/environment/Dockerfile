# syntax=docker/dockerfile:1.7
#
# Lineup OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Lineup native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Lineup writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Lineup app + its autostart launcher.
COPY lineup.py /opt/lineup/lineup.py
COPY start-lineup.sh /opt/lineup/start-lineup.sh
RUN chmod +x /opt/lineup/start-lineup.sh

WORKDIR /app
