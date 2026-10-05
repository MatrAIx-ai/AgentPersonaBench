# syntax=docker/dockerfile:1.7
#
# SlotDock OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SlotDock native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Fill slots", SlotDock writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SlotDock app + its autostart launcher.
COPY slotdock.py /opt/slotdock/slotdock.py
COPY start-slotdock.sh /opt/slotdock/start-slotdock.sh
RUN chmod +x /opt/slotdock/start-slotdock.sh

WORKDIR /app
