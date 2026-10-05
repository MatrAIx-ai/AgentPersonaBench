# syntax=docker/dockerfile:1.7
#
# FolioAndFilm OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FolioAndFilm native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", FolioAndFilm writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FolioAndFilm app + its autostart launcher.
COPY folioandfilm.py /opt/folioandfilm/folioandfilm.py
COPY start-folioandfilm.sh /opt/folioandfilm/start-folioandfilm.sh
RUN chmod +x /opt/folioandfilm/start-folioandfilm.sh

WORKDIR /app
