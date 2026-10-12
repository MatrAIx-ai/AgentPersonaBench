# syntax=docker/dockerfile:1.7
#
# MilestoneHub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MilestoneHub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Enroll", MilestoneHub writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MilestoneHub app + its autostart launcher.
COPY milestonehub.py /opt/milestonehub/milestonehub.py
COPY start-milestonehub.sh /opt/milestonehub/start-milestonehub.sh
RUN chmod +x /opt/milestonehub/start-milestonehub.sh

WORKDIR /app
