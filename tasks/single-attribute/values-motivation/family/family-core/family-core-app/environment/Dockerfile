# syntax=docker/dockerfile:1.7
#
# DateFork OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DateFork native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set RSVPs", DateFork writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DateFork app + its autostart launcher.
COPY datefork.py /opt/datefork/datefork.py
COPY start-datefork.sh /opt/datefork/start-datefork.sh
RUN chmod +x /opt/datefork/start-datefork.sh

WORKDIR /app
