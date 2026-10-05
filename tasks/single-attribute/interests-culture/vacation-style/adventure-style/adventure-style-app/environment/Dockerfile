# syntax=docker/dockerfile:1.7
#
# PortCall OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PortCall native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book shore day", PortCall writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PortCall app + its autostart launcher.
COPY portcall.py /opt/portcall/portcall.py
COPY start-portcall.sh /opt/portcall/start-portcall.sh
RUN chmod +x /opt/portcall/start-portcall.sh

WORKDIR /app
