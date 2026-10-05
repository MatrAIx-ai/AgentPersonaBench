# syntax=docker/dockerfile:1.7
#
# PlanPad OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PlanPad native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, PlanPad writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PlanPad app + its autostart launcher.
COPY planpad.py /opt/planpad/planpad.py
COPY start-planpad.sh /opt/planpad/start-planpad.sh
RUN chmod +x /opt/planpad/start-planpad.sh

WORKDIR /app
