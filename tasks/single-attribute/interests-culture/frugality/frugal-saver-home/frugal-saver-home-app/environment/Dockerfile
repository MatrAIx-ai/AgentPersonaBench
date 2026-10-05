# syntax=docker/dockerfile:1.7
#
# CartNest OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CartNest native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, CartNest writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CartNest app + its autostart launcher.
COPY cartnest.py /opt/cartnest/cartnest.py
COPY start-cartnest.sh /opt/cartnest/start-cartnest.sh
RUN chmod +x /opt/cartnest/start-cartnest.sh

WORKDIR /app
