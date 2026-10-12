# syntax=docker/dockerfile:1.7
#
# StagePlanner OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StagePlanner native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve evenings", StagePlanner writes /app/output/reservations.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StagePlanner app + its autostart launcher.
COPY stageplanner.py /opt/stageplanner/stageplanner.py
COPY start-stageplanner.sh /opt/stageplanner/start-stageplanner.sh
RUN chmod +x /opt/stageplanner/start-stageplanner.sh

WORKDIR /app
