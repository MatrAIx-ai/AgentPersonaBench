# syntax=docker/dockerfile:1.7
#
# QuickSip OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the QuickSip native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user places an order, QuickSip writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The QuickSip app + its autostart launcher.
COPY quicksip.py /opt/quicksip/quicksip.py
COPY start-quicksip.sh /opt/quicksip/start-quicksip.sh
RUN chmod +x /opt/quicksip/start-quicksip.sh

WORKDIR /app
