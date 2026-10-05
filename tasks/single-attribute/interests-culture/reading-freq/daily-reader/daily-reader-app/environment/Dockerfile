# syntax=docker/dockerfile:1.7
#
# ShelfSide OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ShelfSide native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Pack box", ShelfSide writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ShelfSide app + its autostart launcher.
COPY shelfside.py /opt/shelfside/shelfside.py
COPY start-shelfside.sh /opt/shelfside/start-shelfside.sh
RUN chmod +x /opt/shelfside/start-shelfside.sh

WORKDIR /app
