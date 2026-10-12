# syntax=docker/dockerfile:1.7
#
# RailTime OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the RailTime native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Load picks", RailTime writes /app/output/picks.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The RailTime app + its autostart launcher.
COPY railtime.py /opt/railtime/railtime.py
COPY start-railtime.sh /opt/railtime/start-railtime.sh
RUN chmod +x /opt/railtime/start-railtime.sh

WORKDIR /app
