# syntax=docker/dockerfile:1.7
#
# PageForge OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PageForge native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Build site", PageForge writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PageForge app + its autostart launcher.
COPY pageforge.py /opt/pageforge/pageforge.py
COPY start-pageforge.sh /opt/pageforge/start-pageforge.sh
RUN chmod +x /opt/pageforge/start-pageforge.sh

WORKDIR /app
