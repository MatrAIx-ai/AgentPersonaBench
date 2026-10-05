# syntax=docker/dockerfile:1.7
#
# TalkGrid OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TalkGrid native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Build day", TalkGrid writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TalkGrid app + its autostart launcher.
COPY talkgrid.py /opt/talkgrid/talkgrid.py
COPY start-talkgrid.sh /opt/talkgrid/start-talkgrid.sh
RUN chmod +x /opt/talkgrid/start-talkgrid.sh

WORKDIR /app
