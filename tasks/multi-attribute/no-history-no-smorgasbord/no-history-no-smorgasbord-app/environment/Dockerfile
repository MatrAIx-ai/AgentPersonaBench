# syntax=docker/dockerfile:1.7
#
# VenueAndVolume OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the VenueAndVolume native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", VenueAndVolume writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The VenueAndVolume app + its autostart launcher.
COPY venueandvolume.py /opt/venueandvolume/venueandvolume.py
COPY start-venueandvolume.sh /opt/venueandvolume/start-venueandvolume.sh
RUN chmod +x /opt/venueandvolume/start-venueandvolume.sh

WORKDIR /app
