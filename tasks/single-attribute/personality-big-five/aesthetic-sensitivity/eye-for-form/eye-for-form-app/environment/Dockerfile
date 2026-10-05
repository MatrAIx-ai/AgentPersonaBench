# syntax=docker/dockerfile:1.7
#
# StudioBox OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StudioBox native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Order items", StudioBox writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StudioBox app + its autostart launcher.
COPY studiobox.py /opt/studiobox/studiobox.py
COPY start-studiobox.sh /opt/studiobox/start-studiobox.sh
RUN chmod +x /opt/studiobox/start-studiobox.sh

WORKDIR /app
