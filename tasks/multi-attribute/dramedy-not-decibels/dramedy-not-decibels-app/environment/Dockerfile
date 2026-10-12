# syntax=docker/dockerfile:1.7
#
# EveningsTwoPart OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the EveningsTwoPart native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", EveningsTwoPart writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EveningsTwoPart app + its autostart launcher.
COPY eveningstwopart.py /opt/eveningstwopart/eveningstwopart.py
COPY start-eveningstwopart.sh /opt/eveningstwopart/start-eveningstwopart.sh
RUN chmod +x /opt/eveningstwopart/start-eveningstwopart.sh

WORKDIR /app
