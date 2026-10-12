# syntax=docker/dockerfile:1.7
#
# PerkDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PerkDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book pairs", PerkDesk writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PerkDesk app + its autostart launcher.
COPY perkdesk.py /opt/perkdesk/perkdesk.py
COPY start-perkdesk.sh /opt/perkdesk/start-perkdesk.sh
RUN chmod +x /opt/perkdesk/start-perkdesk.sh

WORKDIR /app
