# syntax=docker/dockerfile:1.7
#
# DayPlanner OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DayPlanner native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, DayPlanner writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DayPlanner app + its autostart launcher.
COPY dayplanner.py /opt/dayplanner/dayplanner.py
COPY start-dayplanner.sh /opt/dayplanner/start-dayplanner.sh
RUN chmod +x /opt/dayplanner/start-dayplanner.sh

WORKDIR /app
