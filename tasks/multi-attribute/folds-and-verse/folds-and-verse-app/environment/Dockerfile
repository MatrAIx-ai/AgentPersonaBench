# syntax=docker/dockerfile:1.7
#
# KitsQuiet OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the KitsQuiet native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Choose kits", KitsQuiet writes /app/output/choices.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The KitsQuiet app + its autostart launcher.
COPY kitsquiet.py /opt/kitsquiet/kitsquiet.py
COPY start-kitsquiet.sh /opt/kitsquiet/start-kitsquiet.sh
RUN chmod +x /opt/kitsquiet/start-kitsquiet.sh

WORKDIR /app
