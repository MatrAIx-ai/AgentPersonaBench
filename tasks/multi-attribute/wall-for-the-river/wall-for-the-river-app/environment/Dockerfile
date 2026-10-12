# syntax=docker/dockerfile:1.7
#
# GymBoard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GymBoard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Sign up", GymBoard writes /app/output/signups.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GymBoard app + its autostart launcher.
COPY gymboard.py /opt/gymboard/gymboard.py
COPY start-gymboard.sh /opt/gymboard/start-gymboard.sh
RUN chmod +x /opt/gymboard/start-gymboard.sh

WORKDIR /app
