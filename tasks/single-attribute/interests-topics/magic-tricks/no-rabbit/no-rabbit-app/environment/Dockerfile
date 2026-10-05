# syntax=docker/dockerfile:1.7
#
# TentTickets OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TentTickets native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Claim tickets", TentTickets writes /app/output/tickets.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TentTickets app + its autostart launcher.
COPY tenttickets.py /opt/tenttickets/tenttickets.py
COPY start-tenttickets.sh /opt/tenttickets/start-tenttickets.sh
RUN chmod +x /opt/tenttickets/start-tenttickets.sh

WORKDIR /app
