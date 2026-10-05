# syntax=docker/dockerfile:1.7
#
# NeighbourNet OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NeighbourNet native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set up arrangements", NeighbourNet writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NeighbourNet app + its autostart launcher.
COPY neighbournet.py /opt/neighbournet/neighbournet.py
COPY start-neighbournet.sh /opt/neighbournet/start-neighbournet.sh
RUN chmod +x /opt/neighbournet/start-neighbournet.sh

WORKDIR /app
