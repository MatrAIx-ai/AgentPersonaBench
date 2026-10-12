# syntax=docker/dockerfile:1.7
#
# MeetSpace OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MeetSpace native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user books a room, MeetSpace writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MeetSpace app + its autostart launcher.
COPY meetspace.py /opt/meetspace/meetspace.py
COPY start-meetspace.sh /opt/meetspace/start-meetspace.sh
RUN chmod +x /opt/meetspace/start-meetspace.sh

WORKDIR /app
