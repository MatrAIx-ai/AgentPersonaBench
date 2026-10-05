# syntax=docker/dockerfile:1.7
#
# Coursely OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Coursely native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Coursely writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Coursely app + its autostart launcher.
COPY coursely.py /opt/coursely/coursely.py
COPY start-coursely.sh /opt/coursely/start-coursely.sh
RUN chmod +x /opt/coursely/start-coursely.sh

WORKDIR /app
