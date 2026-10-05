# syntax=docker/dockerfile:1.7
#
# LunchAndBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LunchAndBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", LunchAndBook writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LunchAndBook app + its autostart launcher.
COPY lunchandbook.py /opt/lunchandbook/lunchandbook.py
COPY start-lunchandbook.sh /opt/lunchandbook/start-lunchandbook.sh
RUN chmod +x /opt/lunchandbook/start-lunchandbook.sh

WORKDIR /app
