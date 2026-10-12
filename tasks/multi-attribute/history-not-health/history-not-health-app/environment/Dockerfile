# syntax=docker/dockerfile:1.7
#
# SundayTalksMuseum OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SundayTalksMuseum native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SundayTalksMuseum writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SundayTalksMuseum app + its autostart launcher.
COPY sundaytalksmuseum.py /opt/sundaytalksmuseum/sundaytalksmuseum.py
COPY start-sundaytalksmuseum.sh /opt/sundaytalksmuseum/start-sundaytalksmuseum.sh
RUN chmod +x /opt/sundaytalksmuseum/start-sundaytalksmuseum.sh

WORKDIR /app
