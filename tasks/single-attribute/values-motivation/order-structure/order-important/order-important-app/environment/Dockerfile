# syntax=docker/dockerfile:1.7
#
# ShelfSort OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ShelfSort native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set up home", ShelfSort writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ShelfSort app + its autostart launcher.
COPY shelfsort.py /opt/shelfsort/shelfsort.py
COPY start-shelfsort.sh /opt/shelfsort/start-shelfsort.sh
RUN chmod +x /opt/shelfsort/start-shelfsort.sh

WORKDIR /app
