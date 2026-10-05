# syntax=docker/dockerfile:1.7
# OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool + scrot)
# PLUS the StudioBook GUI. The CUA agent drives it by screenshot + coordinate
# click; when the user confirms the booking, the app writes
# /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Build context is this environment/ dir; studiobook.py here stays byte-identical
# to the canonical input/app/studiobook.py.
COPY studiobook.py /opt/studiobook/studiobook.py
COPY start-studiobook.sh /opt/studiobook/start-studiobook.sh
RUN chmod +x /opt/studiobook/start-studiobook.sh

WORKDIR /app
