# syntax=docker/dockerfile:1.7
#
# TierPick OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TierPick native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Commission", TierPick writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TierPick app + its autostart launcher.
COPY tierpick.py /opt/tierpick/tierpick.py
COPY start-tierpick.sh /opt/tierpick/start-tierpick.sh
RUN chmod +x /opt/tierpick/start-tierpick.sh

WORKDIR /app
