# syntax=docker/dockerfile:1.7
#
# DevToolkit OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DevToolkit native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, DevToolkit writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DevToolkit app + its autostart launcher.
COPY devtoolkit.py /opt/devtoolkit/devtoolkit.py
COPY start-devtoolkit.sh /opt/devtoolkit/start-devtoolkit.sh
RUN chmod +x /opt/devtoolkit/start-devtoolkit.sh

WORKDIR /app
