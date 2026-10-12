# syntax=docker/dockerfile:1.7
# OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool + scrot)
# PLUS the CanteenOrder GUI. The CUA agent drives it by screenshot + coordinate
# click; when the user places the order, the app writes /app/output/order.json.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Build context is this environment/ dir; canteenorder.py here stays byte-identical to
# the canonical input/app/canteenorder.py.
COPY canteenorder.py /opt/canteenorder/canteenorder.py
COPY start-canteenorder.sh /opt/canteenorder/start-canteenorder.sh
RUN chmod +x /opt/canteenorder/start-canteenorder.sh

WORKDIR /app
