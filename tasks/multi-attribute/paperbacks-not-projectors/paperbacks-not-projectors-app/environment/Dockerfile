# syntax=docker/dockerfile:1.7
#
# EveningsClub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the EveningsClub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", EveningsClub writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EveningsClub app + its autostart launcher.
COPY eveningsclub.py /opt/eveningsclub/eveningsclub.py
COPY start-eveningsclub.sh /opt/eveningsclub/start-eveningsclub.sh
RUN chmod +x /opt/eveningsclub/start-eveningsclub.sh

WORKDIR /app
