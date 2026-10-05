# syntax=docker/dockerfile:1.7
#
# SaturdaysCentre OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysCentre native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysCentre writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysCentre app + its autostart launcher.
COPY saturdayscentre.py /opt/saturdayscentre/saturdayscentre.py
COPY start-saturdayscentre.sh /opt/saturdayscentre/start-saturdayscentre.sh
RUN chmod +x /opt/saturdayscentre/start-saturdayscentre.sh

WORKDIR /app
