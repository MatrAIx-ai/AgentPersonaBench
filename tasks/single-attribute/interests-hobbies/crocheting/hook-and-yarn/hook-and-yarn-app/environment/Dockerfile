# syntax=docker/dockerfile:1.7
#
# FairCard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FairCard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Redeem card", FairCard writes /app/output/giftcard.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FairCard app + its autostart launcher.
COPY faircard.py /opt/faircard/faircard.py
COPY start-faircard.sh /opt/faircard/start-faircard.sh
RUN chmod +x /opt/faircard/start-faircard.sh

WORKDIR /app
