# syntax=docker/dockerfile:1.7
#
# Crewboard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Crewboard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Crewboard writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Crewboard app + its autostart launcher.
COPY crewboard.py /opt/crewboard/crewboard.py
COPY start-crewboard.sh /opt/crewboard/start-crewboard.sh
RUN chmod +x /opt/crewboard/start-crewboard.sh

WORKDIR /app
