# syntax=docker/dockerfile:1.7
#
# TrackPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TrackPass native GUI baked in. The CUA agent
# (persona-computer-1) drives it by screenshot + coordinate click; when the
# traveller books, TrackPass writes /app/output/booking.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TrackPass app + its autostart launcher.
COPY trackpass.py /opt/trackpass/trackpass.py
COPY start-trackpass.sh /opt/trackpass/start-trackpass.sh
RUN chmod +x /opt/trackpass/start-trackpass.sh

WORKDIR /app
