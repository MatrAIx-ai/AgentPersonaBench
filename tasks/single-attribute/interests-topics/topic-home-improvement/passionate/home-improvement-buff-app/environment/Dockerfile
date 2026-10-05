# syntax=docker/dockerfile:1.7
#
# Explorer OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Explorer native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Explorer writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Explorer app + its autostart launcher.
COPY explorer.py /opt/explorer/explorer.py
COPY start-explorer.sh /opt/explorer/start-explorer.sh
RUN chmod +x /opt/explorer/start-explorer.sh

WORKDIR /app
