# syntax=docker/dockerfile:1.7
#
# LateAndLanes OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LateAndLanes native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Fridays", LateAndLanes writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LateAndLanes app + its autostart launcher.
COPY lateandlanes.py /opt/lateandlanes/lateandlanes.py
COPY start-lateandlanes.sh /opt/lateandlanes/start-lateandlanes.sh
RUN chmod +x /opt/lateandlanes/start-lateandlanes.sh

WORKDIR /app
