# syntax=docker/dockerfile:1.7
#
# GadgetLab OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GadgetLab native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, GadgetLab writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GadgetLab app + its autostart launcher.
COPY gadgetlab.py /opt/gadgetlab/gadgetlab.py
COPY start-gadgetlab.sh /opt/gadgetlab/start-gadgetlab.sh
RUN chmod +x /opt/gadgetlab/start-gadgetlab.sh

WORKDIR /app
