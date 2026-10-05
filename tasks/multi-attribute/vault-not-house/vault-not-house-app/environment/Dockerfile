# syntax=docker/dockerfile:1.7
#
# FridaysCentre OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FridaysCentre native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Fridays", FridaysCentre writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FridaysCentre app + its autostart launcher.
COPY fridayscentre.py /opt/fridayscentre/fridayscentre.py
COPY start-fridayscentre.sh /opt/fridayscentre/start-fridayscentre.sh
RUN chmod +x /opt/fridayscentre/start-fridayscentre.sh

WORKDIR /app
