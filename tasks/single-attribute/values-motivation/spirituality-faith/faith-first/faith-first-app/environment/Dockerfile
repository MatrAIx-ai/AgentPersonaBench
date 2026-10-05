# syntax=docker/dockerfile:1.7
#
# WeekendDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WeekendDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve slots", WeekendDesk writes /app/output/reservations.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WeekendDesk app + its autostart launcher.
COPY weekenddesk.py /opt/weekenddesk/weekenddesk.py
COPY start-weekenddesk.sh /opt/weekenddesk/start-weekenddesk.sh
RUN chmod +x /opt/weekenddesk/start-weekenddesk.sh

WORKDIR /app
