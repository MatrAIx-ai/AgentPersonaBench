# syntax=docker/dockerfile:1.7
# OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool + scrot)
# PLUS the Kestrel Itinerary Builder GUI. The CUA agent operates it by screenshot
# + coordinate click; when the traveller saves the itinerary, the app writes
# /app/output/itinerary.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Build context is this environment/ dir; kestrel.py here stays byte-identical
# to the canonical input/app/kestrel.py.
COPY kestrel.py /opt/kestrel/kestrel.py
COPY start-app.sh /opt/kestrel/start-app.sh
RUN chmod +x /opt/kestrel/start-app.sh

WORKDIR /app
