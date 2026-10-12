# syntax=docker/dockerfile:1.7
#
# BriefBox OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BriefBox native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Load pack", BriefBox writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BriefBox app + its autostart launcher.
COPY briefbox.py /opt/briefbox/briefbox.py
COPY start-briefbox.sh /opt/briefbox/start-briefbox.sh
RUN chmod +x /opt/briefbox/start-briefbox.sh

WORKDIR /app
