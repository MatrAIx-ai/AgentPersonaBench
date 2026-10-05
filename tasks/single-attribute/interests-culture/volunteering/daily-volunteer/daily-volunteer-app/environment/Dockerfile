# syntax=docker/dockerfile:1.7
#
# BlockBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BlockBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Claim blocks", BlockBook writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BlockBook app + its autostart launcher.
COPY blockbook.py /opt/blockbook/blockbook.py
COPY start-blockbook.sh /opt/blockbook/start-blockbook.sh
RUN chmod +x /opt/blockbook/start-blockbook.sh

WORKDIR /app
