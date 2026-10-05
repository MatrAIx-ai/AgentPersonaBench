# syntax=docker/dockerfile:1.7
#
# BowlAndDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BowlAndDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", BowlAndDesk writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BowlAndDesk app + its autostart launcher.
COPY bowlanddesk.py /opt/bowlanddesk/bowlanddesk.py
COPY start-bowlanddesk.sh /opt/bowlanddesk/start-bowlanddesk.sh
RUN chmod +x /opt/bowlanddesk/start-bowlanddesk.sh

WORKDIR /app
