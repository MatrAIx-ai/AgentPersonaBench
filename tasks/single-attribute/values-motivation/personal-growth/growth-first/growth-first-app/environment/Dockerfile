# syntax=docker/dockerfile:1.7
#
# TermPlanner OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TermPlanner native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Confirm my series", TermPlanner writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TermPlanner app + its autostart launcher.
COPY termplanner.py /opt/termplanner/termplanner.py
COPY start-termplanner.sh /opt/termplanner/start-termplanner.sh
RUN chmod +x /opt/termplanner/start-termplanner.sh

WORKDIR /app
