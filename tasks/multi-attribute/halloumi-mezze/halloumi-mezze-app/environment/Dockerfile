# syntax=docker/dockerfile:1.7
#
# ClubLunch OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClubLunch native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book lunches", ClubLunch writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClubLunch app + its autostart launcher.
COPY clublunch.py /opt/clublunch/clublunch.py
COPY start-clublunch.sh /opt/clublunch/start-clublunch.sh
RUN chmod +x /opt/clublunch/start-clublunch.sh

WORKDIR /app
