# syntax=docker/dockerfile:1.7
#
# AutoPick OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the AutoPick native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms a selection, AutoPick writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The AutoPick app + its autostart launcher.
COPY autopick.py /opt/autopick/autopick.py
COPY start-autopick.sh /opt/autopick/start-autopick.sh
RUN chmod +x /opt/autopick/start-autopick.sh

WORKDIR /app
