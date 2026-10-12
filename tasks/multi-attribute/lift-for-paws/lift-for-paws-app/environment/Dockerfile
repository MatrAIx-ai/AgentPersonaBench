# syntax=docker/dockerfile:1.7
#
# LiftGive OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LiftGive native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Sign up", LiftGive writes /app/output/signups.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LiftGive app + its autostart launcher.
COPY liftgive.py /opt/liftgive/liftgive.py
COPY start-liftgive.sh /opt/liftgive/start-liftgive.sh
RUN chmod +x /opt/liftgive/start-liftgive.sh

WORKDIR /app
