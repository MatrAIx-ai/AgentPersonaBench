# syntax=docker/dockerfile:1.7
#
# HomeStock OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HomeStock native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, HomeStock writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HomeStock app + its autostart launcher.
COPY homestock.py /opt/homestock/homestock.py
COPY start-homestock.sh /opt/homestock/start-homestock.sh
RUN chmod +x /opt/homestock/start-homestock.sh

WORKDIR /app
