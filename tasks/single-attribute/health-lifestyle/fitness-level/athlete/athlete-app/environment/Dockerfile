# syntax=docker/dockerfile:1.7
#
# MotionDeck OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MotionDeck native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve", MotionDeck writes /app/output/reservations.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MotionDeck app + its autostart launcher.
COPY motiondeck.py /opt/motiondeck/motiondeck.py
COPY start-motiondeck.sh /opt/motiondeck/start-motiondeck.sh
RUN chmod +x /opt/motiondeck/start-motiondeck.sh

WORKDIR /app
