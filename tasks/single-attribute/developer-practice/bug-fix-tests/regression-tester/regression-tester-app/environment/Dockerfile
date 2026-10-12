# syntax=docker/dockerfile:1.7
#
# FixBench OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FixBench native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set plan", FixBench writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FixBench app + its autostart launcher.
COPY fixbench.py /opt/fixbench/fixbench.py
COPY start-fixbench.sh /opt/fixbench/start-fixbench.sh
RUN chmod +x /opt/fixbench/start-fixbench.sh

WORKDIR /app
