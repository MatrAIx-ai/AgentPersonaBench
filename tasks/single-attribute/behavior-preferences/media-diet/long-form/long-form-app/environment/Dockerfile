# syntax=docker/dockerfile:1.7
#
# SeatShelf OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SeatShelf native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Download picks", SeatShelf writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SeatShelf app + its autostart launcher.
COPY seatshelf.py /opt/seatshelf/seatshelf.py
COPY start-seatshelf.sh /opt/seatshelf/start-seatshelf.sh
RUN chmod +x /opt/seatshelf/start-seatshelf.sh

WORKDIR /app
