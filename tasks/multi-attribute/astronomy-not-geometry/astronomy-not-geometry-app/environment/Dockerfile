# syntax=docker/dockerfile:1.7
#
# SaturdaysScienceCentre OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysScienceCentre native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysScienceCentre writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysScienceCentre app + its autostart launcher.
COPY saturdayssciencecentre.py /opt/saturdayssciencecentre/saturdayssciencecentre.py
COPY start-saturdayssciencecentre.sh /opt/saturdayssciencecentre/start-saturdayssciencecentre.sh
RUN chmod +x /opt/saturdayssciencecentre/start-saturdayssciencecentre.sh

WORKDIR /app
