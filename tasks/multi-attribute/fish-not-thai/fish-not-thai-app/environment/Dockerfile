# syntax=docker/dockerfile:1.7
#
# ClubOrder OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClubOrder native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Place order", ClubOrder writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClubOrder app + its autostart launcher.
COPY cluborder.py /opt/cluborder/cluborder.py
COPY start-cluborder.sh /opt/cluborder/start-cluborder.sh
RUN chmod +x /opt/cluborder/start-cluborder.sh

WORKDIR /app
