# syntax=docker/dockerfile:1.7
#
# GreenPlate OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GreenPlate native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, GreenPlate writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GreenPlate app + its autostart launcher.
COPY greenplate.py /opt/greenplate/greenplate.py
COPY start-greenplate.sh /opt/greenplate/start-greenplate.sh
RUN chmod +x /opt/greenplate/start-greenplate.sh

WORKDIR /app
