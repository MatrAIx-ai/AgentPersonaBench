# syntax=docker/dockerfile:1.7
#
# EveningPlanner OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE +
# xdotool + scrot) PLUS Python Tkinter and the EveningPlanner native GUI app baked
# in. The CUA agent (persona-computer-1) drives it by screenshot + coordinate
# click; when the user confirms, EveningPlanner writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EveningPlanner app + its autostart launcher.
COPY eveningplanner.py /opt/eveningplanner/eveningplanner.py
COPY start-eveningplanner.sh /opt/eveningplanner/start-eveningplanner.sh
RUN chmod +x /opt/eveningplanner/start-eveningplanner.sh

WORKDIR /app
