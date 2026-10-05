# syntax=docker/dockerfile:1.7
#
# Muse OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Muse native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Muse writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Muse app + its autostart launcher.
COPY muse.py /opt/muse/muse.py
COPY start-muse.sh /opt/muse/start-muse.sh
RUN chmod +x /opt/muse/start-muse.sh

WORKDIR /app
