# syntax=docker/dockerfile:1.7
#
# CanvasDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CanvasDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set Plan", CanvasDesk writes /app/output/studio_plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CanvasDesk app + its autostart launcher.
COPY canvasdesk.py /opt/canvasdesk/canvasdesk.py
COPY start-canvasdesk.sh /opt/canvasdesk/start-canvasdesk.sh
RUN chmod +x /opt/canvasdesk/start-canvasdesk.sh

WORKDIR /app
