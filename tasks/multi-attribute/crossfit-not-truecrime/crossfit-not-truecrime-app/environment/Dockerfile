# syntax=docker/dockerfile:1.7
#
# BookshelfAndArena OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BookshelfAndArena native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book meetups", BookshelfAndArena writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BookshelfAndArena app + its autostart launcher.
COPY bookshelfandarena.py /opt/bookshelfandarena/bookshelfandarena.py
COPY start-bookshelfandarena.sh /opt/bookshelfandarena/start-bookshelfandarena.sh
RUN chmod +x /opt/bookshelfandarena/start-bookshelfandarena.sh

WORKDIR /app
