# syntax=docker/dockerfile:1.7
#
# SaturdayArts OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdayArts native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdayArts writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdayArts app + its autostart launcher.
COPY saturdayarts.py /opt/saturdayarts/saturdayarts.py
COPY start-saturdayarts.sh /opt/saturdayarts/start-saturdayarts.sh
RUN chmod +x /opt/saturdayarts/start-saturdayarts.sh

WORKDIR /app
