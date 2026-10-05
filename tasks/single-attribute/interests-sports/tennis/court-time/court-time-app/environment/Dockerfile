# syntax=docker/dockerfile:1.7
#
# CourtBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CourtBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Confirm bookings", CourtBook writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CourtBook app + its autostart launcher.
COPY courtbook.py /opt/courtbook/courtbook.py
COPY start-courtbook.sh /opt/courtbook/start-courtbook.sh
RUN chmod +x /opt/courtbook/start-courtbook.sh

WORKDIR /app
