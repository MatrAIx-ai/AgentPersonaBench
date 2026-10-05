# syntax=docker/dockerfile:1.7
#
# ThreeRestock OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ThreeRestock native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Buy products", ThreeRestock writes /app/output/basket.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ThreeRestock app + its autostart launcher.
COPY threerestock.py /opt/threerestock/threerestock.py
COPY start-threerestock.sh /opt/threerestock/start-threerestock.sh
RUN chmod +x /opt/threerestock/start-threerestock.sh

WORKDIR /app
