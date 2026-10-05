# syntax=docker/dockerfile:1.7
#
# HubLife OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HubLife native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set up stay", HubLife writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HubLife app + its autostart launcher.
COPY hublife.py /opt/hublife/hublife.py
COPY start-hublife.sh /opt/hublife/start-hublife.sh
RUN chmod +x /opt/hublife/start-hublife.sh

WORKDIR /app
