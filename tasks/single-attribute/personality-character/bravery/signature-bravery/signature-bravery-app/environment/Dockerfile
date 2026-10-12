# syntax=docker/dockerfile:1.7
#
# Crossroads OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Crossroads native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Crossroads writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Crossroads app + its autostart launcher.
COPY crossroads.py /opt/crossroads/crossroads.py
COPY start-crossroads.sh /opt/crossroads/start-crossroads.sh
RUN chmod +x /opt/crossroads/start-crossroads.sh

WORKDIR /app
