# syntax=docker/dockerfile:1.7
#
# NightCard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NightCard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Send order", NightCard writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NightCard app + its autostart launcher.
COPY nightcard.py /opt/nightcard/nightcard.py
COPY start-nightcard.sh /opt/nightcard/start-nightcard.sh
RUN chmod +x /opt/nightcard/start-nightcard.sh

WORKDIR /app
