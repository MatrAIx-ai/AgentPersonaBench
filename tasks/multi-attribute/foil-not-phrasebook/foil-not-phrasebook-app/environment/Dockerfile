# syntax=docker/dockerfile:1.7
#
# CentreCard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CentreCard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", CentreCard writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CentreCard app + its autostart launcher.
COPY centrecard.py /opt/centrecard/centrecard.py
COPY start-centrecard.sh /opt/centrecard/start-centrecard.sh
RUN chmod +x /opt/centrecard/start-centrecard.sh

WORKDIR /app
