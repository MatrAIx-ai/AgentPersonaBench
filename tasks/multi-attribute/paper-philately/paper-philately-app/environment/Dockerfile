# syntax=docker/dockerfile:1.7
#
# FairDayPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FairDayPass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", FairDayPass writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FairDayPass app + its autostart launcher.
COPY fairdaypass.py /opt/fairdaypass/fairdaypass.py
COPY start-fairdaypass.sh /opt/fairdaypass/start-fairdaypass.sh
RUN chmod +x /opt/fairdaypass/start-fairdaypass.sh

WORKDIR /app
