# syntax=docker/dockerfile:1.7
#
# ShelfAndSession OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ShelfAndSession native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", ShelfAndSession writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ShelfAndSession app + its autostart launcher.
COPY shelfandsession.py /opt/shelfandsession/shelfandsession.py
COPY start-shelfandsession.sh /opt/shelfandsession/start-shelfandsession.sh
RUN chmod +x /opt/shelfandsession/start-shelfandsession.sh

WORKDIR /app
