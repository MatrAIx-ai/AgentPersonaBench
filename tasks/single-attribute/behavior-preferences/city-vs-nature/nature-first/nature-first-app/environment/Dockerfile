# syntax=docker/dockerfile:1.7
#
# RoamPlan OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the RoamPlan native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Save my route", RoamPlan writes /app/output/route.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The RoamPlan app + its autostart launcher.
COPY roamplan.py /opt/roamplan/roamplan.py
COPY start-roamplan.sh /opt/roamplan/start-roamplan.sh
RUN chmod +x /opt/roamplan/start-roamplan.sh

WORKDIR /app
