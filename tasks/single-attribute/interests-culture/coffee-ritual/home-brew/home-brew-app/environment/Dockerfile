# syntax=docker/dockerfile:1.7
#
# KettleKit OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the KettleKit native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set my month", KettleKit writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The KettleKit app + its autostart launcher.
COPY kettlekit.py /opt/kettlekit/kettlekit.py
COPY start-kettlekit.sh /opt/kettlekit/start-kettlekit.sh
RUN chmod +x /opt/kettlekit/start-kettlekit.sh

WORKDIR /app
