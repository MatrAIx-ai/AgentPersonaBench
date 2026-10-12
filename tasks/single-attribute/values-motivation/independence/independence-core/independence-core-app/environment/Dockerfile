# syntax=docker/dockerfile:1.7
#
# HelmDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HelmDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set modes", HelmDesk writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HelmDesk app + its autostart launcher.
COPY helmdesk.py /opt/helmdesk/helmdesk.py
COPY start-helmdesk.sh /opt/helmdesk/start-helmdesk.sh
RUN chmod +x /opt/helmdesk/start-helmdesk.sh

WORKDIR /app
