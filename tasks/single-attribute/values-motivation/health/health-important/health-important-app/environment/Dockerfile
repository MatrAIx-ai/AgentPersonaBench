# syntax=docker/dockerfile:1.7
#
# LarderList OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LarderList native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Place order", LarderList writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LarderList app + its autostart launcher.
COPY larderlist.py /opt/larderlist/larderlist.py
COPY start-larderlist.sh /opt/larderlist/start-larderlist.sh
RUN chmod +x /opt/larderlist/start-larderlist.sh

WORKDIR /app
