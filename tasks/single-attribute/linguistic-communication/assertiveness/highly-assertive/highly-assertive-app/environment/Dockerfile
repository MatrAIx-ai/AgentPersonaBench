# syntax=docker/dockerfile:1.7
#
# Playbook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Playbook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Playbook writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Playbook app + its autostart launcher.
COPY playbook.py /opt/playbook/playbook.py
COPY start-playbook.sh /opt/playbook/start-playbook.sh
RUN chmod +x /opt/playbook/start-playbook.sh

WORKDIR /app
