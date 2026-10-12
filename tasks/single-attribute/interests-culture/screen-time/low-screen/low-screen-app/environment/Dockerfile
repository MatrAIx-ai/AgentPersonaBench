# syntax=docker/dockerfile:1.7
#
# HearthPlan OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HearthPlan native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Fill evenings", HearthPlan writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HearthPlan app + its autostart launcher.
COPY hearthplan.py /opt/hearthplan/hearthplan.py
COPY start-hearthplan.sh /opt/hearthplan/start-hearthplan.sh
RUN chmod +x /opt/hearthplan/start-hearthplan.sh

WORKDIR /app
