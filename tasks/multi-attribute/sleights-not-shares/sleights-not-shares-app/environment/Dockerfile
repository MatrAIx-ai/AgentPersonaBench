# syntax=docker/dockerfile:1.7
#
# EveningsCentre OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the EveningsCentre native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book pairs", EveningsCentre writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EveningsCentre app + its autostart launcher.
COPY eveningscentre.py /opt/eveningscentre/eveningscentre.py
COPY start-eveningscentre.sh /opt/eveningscentre/start-eveningscentre.sh
RUN chmod +x /opt/eveningscentre/start-eveningscentre.sh

WORKDIR /app
