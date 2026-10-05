# syntax=docker/dockerfile:1.7
#
# GuardBench OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GuardBench native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Apply choices", GuardBench writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GuardBench app + its autostart launcher.
COPY guardbench.py /opt/guardbench/guardbench.py
COPY start-guardbench.sh /opt/guardbench/start-guardbench.sh
RUN chmod +x /opt/guardbench/start-guardbench.sh

WORKDIR /app
