# syntax=docker/dockerfile:1.7
#
# Draftly OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Draftly native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Draftly writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Draftly app + its autostart launcher.
COPY draftly.py /opt/draftly/draftly.py
COPY start-draftly.sh /opt/draftly/start-draftly.sh
RUN chmod +x /opt/draftly/start-draftly.sh

WORKDIR /app
