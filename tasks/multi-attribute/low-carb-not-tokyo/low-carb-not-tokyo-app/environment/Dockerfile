# syntax=docker/dockerfile:1.7
#
# BoxOrder OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BoxOrder native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Place order", BoxOrder writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BoxOrder app + its autostart launcher.
COPY boxorder.py /opt/boxorder/boxorder.py
COPY start-boxorder.sh /opt/boxorder/start-boxorder.sh
RUN chmod +x /opt/boxorder/start-boxorder.sh

WORKDIR /app
