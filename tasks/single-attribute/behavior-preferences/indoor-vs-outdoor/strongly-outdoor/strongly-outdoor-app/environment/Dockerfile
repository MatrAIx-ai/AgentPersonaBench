# syntax=docker/dockerfile:1.7
#
# TrailDay OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TrailDay native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Save my day", TrailDay writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TrailDay app + its autostart launcher.
COPY trailday.py /opt/trailday/trailday.py
COPY start-trailday.sh /opt/trailday/start-trailday.sh
RUN chmod +x /opt/trailday/start-trailday.sh

WORKDIR /app
