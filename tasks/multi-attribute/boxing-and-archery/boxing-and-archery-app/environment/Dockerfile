# syntax=docker/dockerfile:1.7
#
# ArenaSeasonPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ArenaSeasonPass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Double-Headers", ArenaSeasonPass writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ArenaSeasonPass app + its autostart launcher.
COPY arenaseasonpass.py /opt/arenaseasonpass/arenaseasonpass.py
COPY start-arenaseasonpass.sh /opt/arenaseasonpass/start-arenaseasonpass.sh
RUN chmod +x /opt/arenaseasonpass/start-arenaseasonpass.sh

WORKDIR /app
