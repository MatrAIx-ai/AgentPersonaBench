# syntax=docker/dockerfile:1.7
#
# DraftDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DraftDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user sends, DraftDesk writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DraftDesk app + its autostart launcher.
COPY draftdesk.py /opt/draftdesk/draftdesk.py
COPY start-draftdesk.sh /opt/draftdesk/start-draftdesk.sh
RUN chmod +x /opt/draftdesk/start-draftdesk.sh

WORKDIR /app
