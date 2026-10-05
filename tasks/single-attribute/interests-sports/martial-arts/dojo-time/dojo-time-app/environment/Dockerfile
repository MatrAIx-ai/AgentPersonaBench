# syntax=docker/dockerfile:1.7
#
# CentreWeek OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CentreWeek native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", CentreWeek writes /app/output/sessions.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CentreWeek app + its autostart launcher.
COPY centreweek.py /opt/centreweek/centreweek.py
COPY start-centreweek.sh /opt/centreweek/start-centreweek.sh
RUN chmod +x /opt/centreweek/start-centreweek.sh

WORKDIR /app
