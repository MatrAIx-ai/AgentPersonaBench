# syntax=docker/dockerfile:1.7
#
# ConnectDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ConnectDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click — no DOM,
# no selector, no JS shortcut. When the client taps CONFIRM, ConnectDesk writes
# /app/output/connections.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ConnectDesk app + its autostart launcher.
COPY connectdesk.py /opt/connectdesk/connectdesk.py
COPY start-connectdesk.sh /opt/connectdesk/start-connectdesk.sh
RUN chmod +x /opt/connectdesk/start-connectdesk.sh

WORKDIR /app
