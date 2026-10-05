# syntax=docker/dockerfile:1.7
#
# BuildBoard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BuildBoard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Make calls", BuildBoard writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BuildBoard app + its autostart launcher.
COPY buildboard.py /opt/buildboard/buildboard.py
COPY start-buildboard.sh /opt/buildboard/start-buildboard.sh
RUN chmod +x /opt/buildboard/start-buildboard.sh

WORKDIR /app
