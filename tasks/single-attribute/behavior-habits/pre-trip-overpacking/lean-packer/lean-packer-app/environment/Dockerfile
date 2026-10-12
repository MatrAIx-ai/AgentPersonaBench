# syntax=docker/dockerfile:1.7
#
# BagList OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BagList native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Finalise list", BagList writes /app/output/packlist.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BagList app + its autostart launcher.
COPY baglist.py /opt/baglist/baglist.py
COPY start-baglist.sh /opt/baglist/start-baglist.sh
RUN chmod +x /opt/baglist/start-baglist.sh

WORKDIR /app
