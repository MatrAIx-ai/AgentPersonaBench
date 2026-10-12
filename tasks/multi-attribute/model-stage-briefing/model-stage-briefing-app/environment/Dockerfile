# syntax=docker/dockerfile:1.7
#
# BriefingPlanner OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BriefingPlanner native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve packages", BriefingPlanner writes /app/output/briefing_plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BriefingPlanner app + its autostart launcher.
COPY briefingplanner.py /opt/briefingplanner/briefingplanner.py
COPY start-briefingplanner.sh /opt/briefingplanner/start-briefingplanner.sh
RUN chmod +x /opt/briefingplanner/start-briefingplanner.sh

WORKDIR /app
