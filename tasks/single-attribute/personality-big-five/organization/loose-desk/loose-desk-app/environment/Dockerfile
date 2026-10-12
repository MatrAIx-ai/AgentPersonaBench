# syntax=docker/dockerfile:1.7
#
# DeskKit OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DeskKit native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Send to my desk", DeskKit writes /app/output/addons.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DeskKit app + its autostart launcher.
COPY deskkit.py /opt/deskkit/deskkit.py
COPY start-deskkit.sh /opt/deskkit/start-deskkit.sh
RUN chmod +x /opt/deskkit/start-deskkit.sh

WORKDIR /app
