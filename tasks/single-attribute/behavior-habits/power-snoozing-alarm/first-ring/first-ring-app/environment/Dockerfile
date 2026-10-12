# syntax=docker/dockerfile:1.7
#
# BedsideBox OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BedsideBox native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Build my kit", BedsideBox writes /app/output/kit.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BedsideBox app + its autostart launcher.
COPY bedsidebox.py /opt/bedsidebox/bedsidebox.py
COPY start-bedsidebox.sh /opt/bedsidebox/start-bedsidebox.sh
RUN chmod +x /opt/bedsidebox/start-bedsidebox.sh

WORKDIR /app
