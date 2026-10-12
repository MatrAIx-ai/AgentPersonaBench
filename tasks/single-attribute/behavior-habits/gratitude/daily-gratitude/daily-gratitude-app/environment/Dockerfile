# syntax=docker/dockerfile:1.7
#
# DayNote OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DayNote native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, DayNote writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DayNote app + its autostart launcher.
COPY daynote.py /opt/daynote/daynote.py
COPY start-daynote.sh /opt/daynote/start-daynote.sh
RUN chmod +x /opt/daynote/start-daynote.sh

WORKDIR /app
