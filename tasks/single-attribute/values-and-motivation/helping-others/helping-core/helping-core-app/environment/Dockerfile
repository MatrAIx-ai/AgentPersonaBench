# syntax=docker/dockerfile:1.7
#
# Weekender OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Weekender native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Weekender writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Weekender app + its autostart launcher.
COPY weekender.py /opt/weekender/weekender.py
COPY start-weekender.sh /opt/weekender/start-weekender.sh
RUN chmod +x /opt/weekender/start-weekender.sh

WORKDIR /app
