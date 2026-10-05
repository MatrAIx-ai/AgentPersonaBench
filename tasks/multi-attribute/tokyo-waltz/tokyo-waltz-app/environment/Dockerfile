# syntax=docker/dockerfile:1.7
#
# FloorPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FloorPass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", FloorPass writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FloorPass app + its autostart launcher.
COPY floorpass.py /opt/floorpass/floorpass.py
COPY start-floorpass.sh /opt/floorpass/start-floorpass.sh
RUN chmod +x /opt/floorpass/start-floorpass.sh

WORKDIR /app
