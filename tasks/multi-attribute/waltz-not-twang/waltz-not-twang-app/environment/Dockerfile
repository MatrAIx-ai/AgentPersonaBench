# syntax=docker/dockerfile:1.7
#
# FridaysHall OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FridaysHall native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Fridays", FridaysHall writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FridaysHall app + its autostart launcher.
COPY fridayshall.py /opt/fridayshall/fridayshall.py
COPY start-fridayshall.sh /opt/fridayshall/start-fridayshall.sh
RUN chmod +x /opt/fridayshall/start-fridayshall.sh

WORKDIR /app
