# syntax=docker/dockerfile:1.7
#
# PanPlanner OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PanPlanner native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set weekend", PanPlanner writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PanPlanner app + its autostart launcher.
COPY panplanner.py /opt/panplanner/panplanner.py
COPY start-panplanner.sh /opt/panplanner/start-panplanner.sh
RUN chmod +x /opt/panplanner/start-panplanner.sh

WORKDIR /app
