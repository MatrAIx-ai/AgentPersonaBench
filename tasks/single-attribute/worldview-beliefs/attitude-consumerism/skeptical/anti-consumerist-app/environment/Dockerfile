# syntax=docker/dockerfile:1.7
#
# ThriftWise OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ThriftWise native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, ThriftWise writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ThriftWise app + its autostart launcher.
COPY thriftwise.py /opt/thriftwise/thriftwise.py
COPY start-thriftwise.sh /opt/thriftwise/start-thriftwise.sh
RUN chmod +x /opt/thriftwise/start-thriftwise.sh

WORKDIR /app
