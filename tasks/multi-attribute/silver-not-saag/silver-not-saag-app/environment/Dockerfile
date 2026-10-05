# syntax=docker/dockerfile:1.7
#
# LunchAndCraft OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LunchAndCraft native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", LunchAndCraft writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LunchAndCraft app + its autostart launcher.
COPY lunchandcraft.py /opt/lunchandcraft/lunchandcraft.py
COPY start-lunchandcraft.sh /opt/lunchandcraft/start-lunchandcraft.sh
RUN chmod +x /opt/lunchandcraft/start-lunchandcraft.sh

WORKDIR /app
