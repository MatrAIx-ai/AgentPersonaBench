# syntax=docker/dockerfile:1.7
#
# GuestPortal OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GuestPortal native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Do these", GuestPortal writes /app/output/followups.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GuestPortal app + its autostart launcher.
COPY guestportal.py /opt/guestportal/guestportal.py
COPY start-guestportal.sh /opt/guestportal/start-guestportal.sh
RUN chmod +x /opt/guestportal/start-guestportal.sh

WORKDIR /app
