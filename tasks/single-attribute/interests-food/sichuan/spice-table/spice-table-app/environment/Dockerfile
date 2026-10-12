# syntax=docker/dockerfile:1.7
#
# LunchPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LunchPass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book lunches", LunchPass writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LunchPass app + its autostart launcher.
COPY lunchpass.py /opt/lunchpass/lunchpass.py
COPY start-lunchpass.sh /opt/lunchpass/start-lunchpass.sh
RUN chmod +x /opt/lunchpass/start-lunchpass.sh

WORKDIR /app
