# syntax=docker/dockerfile:1.7
#
# DuskDial OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DuskDial native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set lineup", DuskDial writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DuskDial app + its autostart launcher.
COPY duskdial.py /opt/duskdial/duskdial.py
COPY start-duskdial.sh /opt/duskdial/start-duskdial.sh
RUN chmod +x /opt/duskdial/start-duskdial.sh

WORKDIR /app
