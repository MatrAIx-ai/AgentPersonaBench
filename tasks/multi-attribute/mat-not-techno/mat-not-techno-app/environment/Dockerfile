# syntax=docker/dockerfile:1.7
#
# SaturdaysSportsHall OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysSportsHall native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysSportsHall writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysSportsHall app + its autostart launcher.
COPY saturdayssportshall.py /opt/saturdayssportshall/saturdayssportshall.py
COPY start-saturdayssportshall.sh /opt/saturdayssportshall/start-saturdayssportshall.sh
RUN chmod +x /opt/saturdayssportshall/start-saturdayssportshall.sh

WORKDIR /app
