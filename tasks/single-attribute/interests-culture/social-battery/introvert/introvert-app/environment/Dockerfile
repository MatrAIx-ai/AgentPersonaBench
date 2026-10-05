# syntax=docker/dockerfile:1.7
#
# RSVPDeck OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the RSVPDeck native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Send RSVPs", RSVPDeck writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The RSVPDeck app + its autostart launcher.
COPY rsvpdeck.py /opt/rsvpdeck/rsvpdeck.py
COPY start-rsvpdeck.sh /opt/rsvpdeck/start-rsvpdeck.sh
RUN chmod +x /opt/rsvpdeck/start-rsvpdeck.sh

WORKDIR /app
