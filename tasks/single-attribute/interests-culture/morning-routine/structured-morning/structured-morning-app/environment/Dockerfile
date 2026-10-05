# syntax=docker/dockerfile:1.7
#
# DawnSlate OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DawnSlate native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set morning", DawnSlate writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DawnSlate app + its autostart launcher.
COPY dawnslate.py /opt/dawnslate/dawnslate.py
COPY start-dawnslate.sh /opt/dawnslate/start-dawnslate.sh
RUN chmod +x /opt/dawnslate/start-dawnslate.sh

WORKDIR /app
