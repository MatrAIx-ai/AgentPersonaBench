# syntax=docker/dockerfile:1.7
#
# StageAndReel OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StageAndReel native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", StageAndReel writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StageAndReel app + its autostart launcher.
COPY stageandreel.py /opt/stageandreel/stageandreel.py
COPY start-stageandreel.sh /opt/stageandreel/start-stageandreel.sh
RUN chmod +x /opt/stageandreel/start-stageandreel.sh

WORKDIR /app
