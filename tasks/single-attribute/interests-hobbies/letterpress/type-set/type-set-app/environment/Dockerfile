# syntax=docker/dockerfile:1.7
#
# StudioDay OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StudioDay native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", StudioDay writes /app/output/sessions.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StudioDay app + its autostart launcher.
COPY studioday.py /opt/studioday/studioday.py
COPY start-studioday.sh /opt/studioday/start-studioday.sh
RUN chmod +x /opt/studioday/start-studioday.sh

WORKDIR /app
