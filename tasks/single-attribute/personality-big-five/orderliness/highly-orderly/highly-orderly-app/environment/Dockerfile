# syntax=docker/dockerfile:1.7
#
# Deskly OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Deskly native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Deskly writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Deskly app + its autostart launcher.
COPY deskly.py /opt/deskly/deskly.py
COPY start-deskly.sh /opt/deskly/start-deskly.sh
RUN chmod +x /opt/deskly/start-deskly.sh

WORKDIR /app
