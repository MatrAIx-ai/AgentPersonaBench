# syntax=docker/dockerfile:1.7
#
# WorkTopper OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WorkTopper native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set workspace", WorkTopper writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WorkTopper app + its autostart launcher.
COPY worktopper.py /opt/worktopper/worktopper.py
COPY start-worktopper.sh /opt/worktopper/start-worktopper.sh
RUN chmod +x /opt/worktopper/start-worktopper.sh

WORKDIR /app
