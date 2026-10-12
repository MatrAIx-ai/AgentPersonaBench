# syntax=docker/dockerfile:1.7
#
# Digest OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Digest native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Digest writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Digest app + its autostart launcher.
COPY digest.py /opt/digest/digest.py
COPY start-digest.sh /opt/digest/start-digest.sh
RUN chmod +x /opt/digest/start-digest.sh

WORKDIR /app
