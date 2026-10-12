# syntax=docker/dockerfile:1.7
#
# HalvesTwo OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HalvesTwo native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", HalvesTwo writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HalvesTwo app + its autostart launcher.
COPY halvestwo.py /opt/halvestwo/halvestwo.py
COPY start-halvestwo.sh /opt/halvestwo/start-halvestwo.sh
RUN chmod +x /opt/halvestwo/start-halvestwo.sh

WORKDIR /app
