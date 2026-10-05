# syntax=docker/dockerfile:1.7
#
# Mingle OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Mingle native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Mingle writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Mingle app + its autostart launcher.
COPY mingle.py /opt/mingle/mingle.py
COPY start-mingle.sh /opt/mingle/start-mingle.sh
RUN chmod +x /opt/mingle/start-mingle.sh

WORKDIR /app
