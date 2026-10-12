# syntax=docker/dockerfile:1.7
#
# HallAndBench OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HallAndBench native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", HallAndBench writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HallAndBench app + its autostart launcher.
COPY hallandbench.py /opt/hallandbench/hallandbench.py
COPY start-hallandbench.sh /opt/hallandbench/start-hallandbench.sh
RUN chmod +x /opt/hallandbench/start-hallandbench.sh

WORKDIR /app
