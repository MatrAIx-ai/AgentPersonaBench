# syntax=docker/dockerfile:1.7
#
# GuestCard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GuestCard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set choices", GuestCard writes /app/output/choices.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GuestCard app + its autostart launcher.
COPY guestcard.py /opt/guestcard/guestcard.py
COPY start-guestcard.sh /opt/guestcard/start-guestcard.sh
RUN chmod +x /opt/guestcard/start-guestcard.sh

WORKDIR /app
