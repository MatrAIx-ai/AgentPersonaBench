# syntax=docker/dockerfile:1.7
#
# RoleBoard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the RoleBoard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Claim roles", RoleBoard writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The RoleBoard app + its autostart launcher.
COPY roleboard.py /opt/roleboard/roleboard.py
COPY start-roleboard.sh /opt/roleboard/start-roleboard.sh
RUN chmod +x /opt/roleboard/start-roleboard.sh

WORKDIR /app
