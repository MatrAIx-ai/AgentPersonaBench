# syntax=docker/dockerfile:1.7
#
# HallAndWick OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HallAndWick native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", HallAndWick writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HallAndWick app + its autostart launcher.
COPY hallandwick.py /opt/hallandwick/hallandwick.py
COPY start-hallandwick.sh /opt/hallandwick/start-hallandwick.sh
RUN chmod +x /opt/hallandwick/start-hallandwick.sh

WORKDIR /app
