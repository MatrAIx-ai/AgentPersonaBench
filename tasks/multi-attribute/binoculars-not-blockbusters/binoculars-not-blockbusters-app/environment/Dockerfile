# syntax=docker/dockerfile:1.7
#
# SaturdaysReserve OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysReserve native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysReserve writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysReserve app + its autostart launcher.
COPY saturdaysreserve.py /opt/saturdaysreserve/saturdaysreserve.py
COPY start-saturdaysreserve.sh /opt/saturdaysreserve/start-saturdaysreserve.sh
RUN chmod +x /opt/saturdaysreserve/start-saturdaysreserve.sh

WORKDIR /app
