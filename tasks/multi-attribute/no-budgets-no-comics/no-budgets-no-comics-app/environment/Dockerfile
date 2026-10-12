# syntax=docker/dockerfile:1.7
#
# ShelfAndWorkshop OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ShelfAndWorkshop native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", ShelfAndWorkshop writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ShelfAndWorkshop app + its autostart launcher.
COPY shelfandworkshop.py /opt/shelfandworkshop/shelfandworkshop.py
COPY start-shelfandworkshop.sh /opt/shelfandworkshop/start-shelfandworkshop.sh
RUN chmod +x /opt/shelfandworkshop/start-shelfandworkshop.sh

WORKDIR /app
