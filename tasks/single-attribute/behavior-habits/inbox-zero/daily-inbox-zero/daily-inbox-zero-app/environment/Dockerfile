# syntax=docker/dockerfile:1.7
#
# Inboxly OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Inboxly native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Inboxly writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Inboxly app + its autostart launcher.
COPY inboxly.py /opt/inboxly/inboxly.py
COPY start-inboxly.sh /opt/inboxly/start-inboxly.sh
RUN chmod +x /opt/inboxly/start-inboxly.sh

WORKDIR /app
