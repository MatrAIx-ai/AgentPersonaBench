# syntax=docker/dockerfile:1.7
#
# Nightly OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Nightly native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Nightly writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Nightly app + its autostart launcher.
COPY nightly.py /opt/nightly/nightly.py
COPY start-nightly.sh /opt/nightly/start-nightly.sh
RUN chmod +x /opt/nightly/start-nightly.sh

WORKDIR /app
