# syntax=docker/dockerfile:1.7
#
# FridayPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FridayPass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Fridays", FridayPass writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FridayPass app + its autostart launcher.
COPY fridaypass.py /opt/fridaypass/fridaypass.py
COPY start-fridaypass.sh /opt/fridaypass/start-fridaypass.sh
RUN chmod +x /opt/fridaypass/start-fridaypass.sh

WORKDIR /app
