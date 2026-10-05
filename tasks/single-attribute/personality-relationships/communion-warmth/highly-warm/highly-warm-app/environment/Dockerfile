# syntax=docker/dockerfile:1.7
#
# Circle OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Circle native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Circle writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Circle app + its autostart launcher.
COPY circle.py /opt/circle/circle.py
COPY start-circle.sh /opt/circle/start-circle.sh
RUN chmod +x /opt/circle/start-circle.sh

WORKDIR /app
