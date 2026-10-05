# syntax=docker/dockerfile:1.7
#
# GuideBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GuideBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, GuideBook writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GuideBook app + its autostart launcher.
COPY guidebook.py /opt/guidebook/guidebook.py
COPY start-guidebook.sh /opt/guidebook/start-guidebook.sh
RUN chmod +x /opt/guidebook/start-guidebook.sh

WORKDIR /app
