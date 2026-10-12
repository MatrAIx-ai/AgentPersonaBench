# syntax=docker/dockerfile:1.7
#
# ScoreRoom OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScoreRoom native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Add to Plan", ScoreRoom writes /app/output/practice_plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScoreRoom app + its autostart launcher.
COPY scoreroom.py /opt/scoreroom/scoreroom.py
COPY start-scoreroom.sh /opt/scoreroom/start-scoreroom.sh
RUN chmod +x /opt/scoreroom/start-scoreroom.sh

WORKDIR /app
