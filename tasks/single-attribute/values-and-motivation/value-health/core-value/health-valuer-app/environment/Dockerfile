# syntax=docker/dockerfile:1.7
#
# SmartCart OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SmartCart native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user checks out, SmartCart writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SmartCart app + its autostart launcher.
COPY smartcart.py /opt/smartcart/smartcart.py
COPY start-smartcart.sh /opt/smartcart/start-smartcart.sh
RUN chmod +x /opt/smartcart/start-smartcart.sh

WORKDIR /app
