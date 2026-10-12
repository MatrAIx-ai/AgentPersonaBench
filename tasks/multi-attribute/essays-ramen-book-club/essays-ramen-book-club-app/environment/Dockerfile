# syntax=docker/dockerfile:1.7
#
# BookClubDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve", the app writes /app/output/pilot_reservations.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BookClubDesk app + its autostart launcher.
COPY pilotstudio.py /opt/pilotstudio/pilotstudio.py
COPY start-pilotstudio.sh /opt/pilotstudio/start-pilotstudio.sh
RUN chmod +x /opt/pilotstudio/start-pilotstudio.sh

WORKDIR /app
