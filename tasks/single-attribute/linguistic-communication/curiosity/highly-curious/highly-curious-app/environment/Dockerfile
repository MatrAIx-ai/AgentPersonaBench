# syntax=docker/dockerfile:1.7
#
# Wander OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Wander native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Wander writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Wander app + its autostart launcher.
COPY wander.py /opt/wander/wander.py
COPY start-wander.sh /opt/wander/start-wander.sh
RUN chmod +x /opt/wander/start-wander.sh

WORKDIR /app
