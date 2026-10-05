# syntax=docker/dockerfile:1.7
#
# BenchBox OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BenchBox native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Spend card", BenchBox writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BenchBox app + its autostart launcher.
COPY benchbox.py /opt/benchbox/benchbox.py
COPY start-benchbox.sh /opt/benchbox/start-benchbox.sh
RUN chmod +x /opt/benchbox/start-benchbox.sh

WORKDIR /app
