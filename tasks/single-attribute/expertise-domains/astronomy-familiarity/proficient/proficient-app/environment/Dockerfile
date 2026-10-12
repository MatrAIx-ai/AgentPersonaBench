# syntax=docker/dockerfile:1.7
#
# PeriodoScope OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE +
# xdotool + scrot) PLUS Python Tkinter and the PeriodoScope native GUI app baked
# in. The CUA agent (persona-computer-1) drives it by screenshot + coordinate
# click; when the user submits the follow-up list, PeriodoScope writes
# /app/output/submission.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY periodoscope.py /opt/periodoscope/periodoscope.py
COPY start-periodoscope.sh /opt/periodoscope/start-periodoscope.sh
RUN chmod +x /opt/periodoscope/start-periodoscope.sh

WORKDIR /app
