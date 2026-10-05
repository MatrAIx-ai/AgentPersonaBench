# syntax=docker/dockerfile:1.7
#
# PhotoKeep OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PhotoKeep native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user organizes the library, PhotoKeep writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PhotoKeep app + its autostart launcher.
COPY photokeep.py /opt/photokeep/photokeep.py
COPY start-photokeep.sh /opt/photokeep/start-photokeep.sh
RUN chmod +x /opt/photokeep/start-photokeep.sh

WORKDIR /app
