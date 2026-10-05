# syntax=docker/dockerfile:1.7
#
# CraftCart OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CraftCart native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Spend vouchers", CraftCart writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CraftCart app + its autostart launcher.
COPY craftcart.py /opt/craftcart/craftcart.py
COPY start-craftcart.sh /opt/craftcart/start-craftcart.sh
RUN chmod +x /opt/craftcart/start-craftcart.sh

WORKDIR /app
