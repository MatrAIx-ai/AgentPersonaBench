# syntax=docker/dockerfile:1.7
#
# SipSpot OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SipSpot native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, SipSpot writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SipSpot app + its autostart launcher.
COPY sipspot.py /opt/sipspot/sipspot.py
COPY start-sipspot.sh /opt/sipspot/start-sipspot.sh
RUN chmod +x /opt/sipspot/start-sipspot.sh

WORKDIR /app
