# syntax=docker/dockerfile:1.7
#
# HearthFeast OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HearthFeast native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set the feast", HearthFeast writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HearthFeast app + its autostart launcher.
COPY hearthfeast.py /opt/hearthfeast/hearthfeast.py
COPY start-hearthfeast.sh /opt/hearthfeast/start-hearthfeast.sh
RUN chmod +x /opt/hearthfeast/start-hearthfeast.sh

WORKDIR /app
