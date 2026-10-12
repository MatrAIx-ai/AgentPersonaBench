# syntax=docker/dockerfile:1.7
#
# ChatComposer OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE +
# xdotool + scrot) PLUS Python Tkinter and the ChatComposer native GUI app baked
# in. The CUA agent (persona-computer-1) drives it by screenshot + coordinate
# click; when the user sends a reply, ChatComposer writes /app/output/order.json
# itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ChatComposer app + its autostart launcher.
COPY chatcomposer.py /opt/chatcomposer/chatcomposer.py
COPY start-chatcomposer.sh /opt/chatcomposer/start-chatcomposer.sh
RUN chmod +x /opt/chatcomposer/start-chatcomposer.sh

WORKDIR /app
