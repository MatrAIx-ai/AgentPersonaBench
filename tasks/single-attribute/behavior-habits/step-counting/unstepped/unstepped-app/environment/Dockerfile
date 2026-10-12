# syntax=docker/dockerfile:1.7
#
# ClubKit OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClubKit native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Claim add-ons", ClubKit writes /app/output/addons.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClubKit app + its autostart launcher.
COPY clubkit.py /opt/clubkit/clubkit.py
COPY start-clubkit.sh /opt/clubkit/start-clubkit.sh
RUN chmod +x /opt/clubkit/start-clubkit.sh

WORKDIR /app
