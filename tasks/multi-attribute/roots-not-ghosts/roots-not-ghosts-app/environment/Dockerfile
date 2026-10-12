# syntax=docker/dockerfile:1.7
#
# RoomsReading OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the RoomsReading native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", RoomsReading writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The RoomsReading app + its autostart launcher.
COPY roomsreading.py /opt/roomsreading/roomsreading.py
COPY start-roomsreading.sh /opt/roomsreading/start-roomsreading.sh
RUN chmod +x /opt/roomsreading/start-roomsreading.sh

WORKDIR /app
