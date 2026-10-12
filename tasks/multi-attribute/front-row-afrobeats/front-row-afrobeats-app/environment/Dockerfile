# syntax=docker/dockerfile:1.7
#
# GigPicks OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GigPicks native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book tickets", GigPicks writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GigPicks app + its autostart launcher.
COPY gigpicks.py /opt/gigpicks/gigpicks.py
COPY start-gigpicks.sh /opt/gigpicks/start-gigpicks.sh
RUN chmod +x /opt/gigpicks/start-gigpicks.sh

WORKDIR /app
