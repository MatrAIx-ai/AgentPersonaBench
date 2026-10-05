# syntax=docker/dockerfile:1.7
#
# StageAndPaper OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StageAndPaper native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", StageAndPaper writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StageAndPaper app + its autostart launcher.
COPY stageandpaper.py /opt/stageandpaper/stageandpaper.py
COPY start-stageandpaper.sh /opt/stageandpaper/start-stageandpaper.sh
RUN chmod +x /opt/stageandpaper/start-stageandpaper.sh

WORKDIR /app
