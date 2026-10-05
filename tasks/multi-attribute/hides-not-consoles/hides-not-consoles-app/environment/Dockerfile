# syntax=docker/dockerfile:1.7
#
# DaysReserve OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DaysReserve native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", DaysReserve writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DaysReserve app + its autostart launcher.
COPY daysreserve.py /opt/daysreserve/daysreserve.py
COPY start-daysreserve.sh /opt/daysreserve/start-daysreserve.sh
RUN chmod +x /opt/daysreserve/start-daysreserve.sh

WORKDIR /app
