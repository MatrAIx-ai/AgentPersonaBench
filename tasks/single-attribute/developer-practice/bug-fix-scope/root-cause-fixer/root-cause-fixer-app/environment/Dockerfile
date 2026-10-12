# syntax=docker/dockerfile:1.7
#
# CauseBoard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CauseBoard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set plan", CauseBoard writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CauseBoard app + its autostart launcher.
COPY causeboard.py /opt/causeboard/causeboard.py
COPY start-causeboard.sh /opt/causeboard/start-causeboard.sh
RUN chmod +x /opt/causeboard/start-causeboard.sh

WORKDIR /app
