# syntax=docker/dockerfile:1.7
#
# LuxeCart OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LuxeCart native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user checks out, LuxeCart writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LuxeCart app + its autostart launcher.
COPY luxecart.py /opt/luxecart/luxecart.py
COPY start-luxecart.sh /opt/luxecart/start-luxecart.sh
RUN chmod +x /opt/luxecart/start-luxecart.sh

WORKDIR /app
