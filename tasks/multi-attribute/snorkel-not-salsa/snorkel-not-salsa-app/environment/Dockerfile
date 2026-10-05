# syntax=docker/dockerfile:1.7
#
# TerraceAndReef OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TerraceAndReef native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book day passes", TerraceAndReef writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TerraceAndReef app + its autostart launcher.
COPY terraceandreef.py /opt/terraceandreef/terraceandreef.py
COPY start-terraceandreef.sh /opt/terraceandreef/start-terraceandreef.sh
RUN chmod +x /opt/terraceandreef/start-terraceandreef.sh

WORKDIR /app
