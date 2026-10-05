# syntax=docker/dockerfile:1.7
#
# Getaway OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Getaway native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Getaway writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Getaway app + its autostart launcher.
COPY getaway.py /opt/getaway/getaway.py
COPY start-getaway.sh /opt/getaway/start-getaway.sh
RUN chmod +x /opt/getaway/start-getaway.sh

WORKDIR /app
