# syntax=docker/dockerfile:1.7
#
# LatesMuseum OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LatesMuseum native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", LatesMuseum writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LatesMuseum app + its autostart launcher.
COPY latesmuseum.py /opt/latesmuseum/latesmuseum.py
COPY start-latesmuseum.sh /opt/latesmuseum/start-latesmuseum.sh
RUN chmod +x /opt/latesmuseum/start-latesmuseum.sh

WORKDIR /app
