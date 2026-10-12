# syntax=docker/dockerfile:1.7
#
# EveningShelf OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool
# + scrot) PLUS Python Tkinter and the EveningShelf native GUI app baked in. The
# CUA agent (persona-computer-1) drives it by screenshot + coordinate click; when
# the user checks out, EveningShelf writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EveningShelf app + its autostart launcher.
COPY eveningshelf.py /opt/eveningshelf/eveningshelf.py
COPY start-eveningshelf.sh /opt/eveningshelf/start-eveningshelf.sh
RUN chmod +x /opt/eveningshelf/start-eveningshelf.sh

WORKDIR /app
