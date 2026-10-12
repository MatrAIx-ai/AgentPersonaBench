# syntax=docker/dockerfile:1.7
#
# PromoLunch OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PromoLunch native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Place pre-order", PromoLunch writes /app/output/preorder.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PromoLunch app + its autostart launcher.
COPY promolunch.py /opt/promolunch/promolunch.py
COPY start-promolunch.sh /opt/promolunch/start-promolunch.sh
RUN chmod +x /opt/promolunch/start-promolunch.sh

WORKDIR /app
