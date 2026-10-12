# syntax=docker/dockerfile:1.7
#
# StageAndCounter OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StageAndCounter native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", StageAndCounter writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StageAndCounter app + its autostart launcher.
COPY stageandcounter.py /opt/stageandcounter/stageandcounter.py
COPY start-stageandcounter.sh /opt/stageandcounter/start-stageandcounter.sh
RUN chmod +x /opt/stageandcounter/start-stageandcounter.sh

WORKDIR /app
