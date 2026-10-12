# syntax=docker/dockerfile:1.7
#
# StageAndTrail OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StageAndTrail native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", StageAndTrail writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StageAndTrail app + its autostart launcher.
COPY stageandtrail.py /opt/stageandtrail/stageandtrail.py
COPY start-stageandtrail.sh /opt/stageandtrail/start-stageandtrail.sh
RUN chmod +x /opt/stageandtrail/start-stageandtrail.sh

WORKDIR /app
