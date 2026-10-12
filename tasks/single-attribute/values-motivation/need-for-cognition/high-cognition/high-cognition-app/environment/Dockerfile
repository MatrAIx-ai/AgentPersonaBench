# syntax=docker/dockerfile:1.7
#
# QueueNight OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the QueueNight native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Queue picks", QueueNight writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The QueueNight app + its autostart launcher.
COPY queuenight.py /opt/queuenight/queuenight.py
COPY start-queuenight.sh /opt/queuenight/start-queuenight.sh
RUN chmod +x /opt/queuenight/start-queuenight.sh

WORKDIR /app
