# syntax=docker/dockerfile:1.7
#
# DeckAndDiamond OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DeckAndDiamond native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", DeckAndDiamond writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DeckAndDiamond app + its autostart launcher.
COPY deckanddiamond.py /opt/deckanddiamond/deckanddiamond.py
COPY start-deckanddiamond.sh /opt/deckanddiamond/start-deckanddiamond.sh
RUN chmod +x /opt/deckanddiamond/start-deckanddiamond.sh

WORKDIR /app
