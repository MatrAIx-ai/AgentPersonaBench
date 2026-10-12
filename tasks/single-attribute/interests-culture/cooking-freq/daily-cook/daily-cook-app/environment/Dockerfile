# syntax=docker/dockerfile:1.7
#
# StovePlan OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StovePlan native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set dinners", StovePlan writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StovePlan app + its autostart launcher.
COPY stoveplan.py /opt/stoveplan/stoveplan.py
COPY start-stoveplan.sh /opt/stoveplan/start-stoveplan.sh
RUN chmod +x /opt/stoveplan/start-stoveplan.sh

WORKDIR /app
