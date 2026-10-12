# syntax=docker/dockerfile:1.7
#
# MorningCard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MorningCard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set morning", MorningCard writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MorningCard app + its autostart launcher.
COPY morningcard.py /opt/morningcard/morningcard.py
COPY start-morningcard.sh /opt/morningcard/start-morningcard.sh
RUN chmod +x /opt/morningcard/start-morningcard.sh

WORKDIR /app
