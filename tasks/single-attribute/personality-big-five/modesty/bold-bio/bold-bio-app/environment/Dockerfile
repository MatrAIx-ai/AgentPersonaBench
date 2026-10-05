# syntax=docker/dockerfile:1.7
#
# ProfileDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ProfileDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Publish profile", ProfileDesk writes /app/output/profile.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ProfileDesk app + its autostart launcher.
COPY profiledesk.py /opt/profiledesk/profiledesk.py
COPY start-profiledesk.sh /opt/profiledesk/start-profiledesk.sh
RUN chmod +x /opt/profiledesk/start-profiledesk.sh

WORKDIR /app
