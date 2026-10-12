# syntax=docker/dockerfile:1.7
#
# Nestly OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Nestly native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Nestly writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Nestly app + its autostart launcher.
COPY nestly.py /opt/nestly/nestly.py
COPY start-nestly.sh /opt/nestly/start-nestly.sh
RUN chmod +x /opt/nestly/start-nestly.sh

WORKDIR /app
