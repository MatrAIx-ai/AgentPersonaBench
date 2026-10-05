# syntax=docker/dockerfile:1.7
#
# SaturdayMakers OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdayMakers native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdayMakers writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdayMakers app + its autostart launcher.
COPY saturdaymakers.py /opt/saturdaymakers/saturdaymakers.py
COPY start-saturdaymakers.sh /opt/saturdaymakers/start-saturdaymakers.sh
RUN chmod +x /opt/saturdaymakers/start-saturdaymakers.sh

WORKDIR /app
