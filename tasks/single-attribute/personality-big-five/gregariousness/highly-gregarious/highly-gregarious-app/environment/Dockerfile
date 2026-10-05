# syntax=docker/dockerfile:1.7
#
# Gatherly OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Gatherly native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Gatherly writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Gatherly app + its autostart launcher.
COPY gatherly.py /opt/gatherly/gatherly.py
COPY start-gatherly.sh /opt/gatherly/start-gatherly.sh
RUN chmod +x /opt/gatherly/start-gatherly.sh

WORKDIR /app
