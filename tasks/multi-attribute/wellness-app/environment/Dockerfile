# syntax=docker/dockerfile:1.7
#
# FitClub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FitClub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms the setup, FitClub writes /app/output/booking.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FitClub app + its autostart launcher.
COPY fitclub.py /opt/fitclub/fitclub.py
COPY start-fitclub.sh /opt/fitclub/start-fitclub.sh
RUN chmod +x /opt/fitclub/start-fitclub.sh

WORKDIR /app
