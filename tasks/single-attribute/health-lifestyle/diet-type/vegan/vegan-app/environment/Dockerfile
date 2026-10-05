# syntax=docker/dockerfile:1.7
#
# QuickBite OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the QuickBite native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, QuickBite writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The QuickBite app + its autostart launcher.
COPY quickbite.py /opt/quickbite/quickbite.py
COPY start-quickbite.sh /opt/quickbite/start-quickbite.sh
RUN chmod +x /opt/quickbite/start-quickbite.sh

WORKDIR /app
