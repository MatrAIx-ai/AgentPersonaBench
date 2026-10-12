# syntax=docker/dockerfile:1.7
#
# StallsApp OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StallsApp native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve shows", StallsApp writes /app/output/reservations.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StallsApp app + its autostart launcher.
COPY stallsapp.py /opt/stallsapp/stallsapp.py
COPY start-stallsapp.sh /opt/stallsapp/start-stallsapp.sh
RUN chmod +x /opt/stallsapp/start-stallsapp.sh

WORKDIR /app
