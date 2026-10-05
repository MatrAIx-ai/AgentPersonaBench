# syntax=docker/dockerfile:1.7
#
# PantryPal OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PantryPal native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Place restock", PantryPal writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PantryPal app + its autostart launcher.
COPY pantrypal.py /opt/pantrypal/pantrypal.py
COPY start-pantrypal.sh /opt/pantrypal/start-pantrypal.sh
RUN chmod +x /opt/pantrypal/start-pantrypal.sh

WORKDIR /app
