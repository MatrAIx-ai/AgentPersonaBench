# syntax=docker/dockerfile:1.7
#
# GateList OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GateList native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set checklist", GateList writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GateList app + its autostart launcher.
COPY gatelist.py /opt/gatelist/gatelist.py
COPY start-gatelist.sh /opt/gatelist/start-gatelist.sh
RUN chmod +x /opt/gatelist/start-gatelist.sh

WORKDIR /app
