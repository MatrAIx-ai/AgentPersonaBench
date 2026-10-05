# syntax=docker/dockerfile:1.7
#
# Curio OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Curio native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Curio writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Curio app + its autostart launcher.
COPY curio.py /opt/curio/curio.py
COPY start-curio.sh /opt/curio/start-curio.sh
RUN chmod +x /opt/curio/start-curio.sh

WORKDIR /app
