# syntax=docker/dockerfile:1.7
#
# Voyager OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Voyager native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Voyager writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Voyager app + its autostart launcher.
COPY voyager.py /opt/voyager/voyager.py
COPY start-voyager.sh /opt/voyager/start-voyager.sh
RUN chmod +x /opt/voyager/start-voyager.sh

WORKDIR /app
