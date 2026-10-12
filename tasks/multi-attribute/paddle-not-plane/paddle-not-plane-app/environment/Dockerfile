# syntax=docker/dockerfile:1.7
#
# WorkshopAndWater OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WorkshopAndWater native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", WorkshopAndWater writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WorkshopAndWater app + its autostart launcher.
COPY workshopandwater.py /opt/workshopandwater/workshopandwater.py
COPY start-workshopandwater.sh /opt/workshopandwater/start-workshopandwater.sh
RUN chmod +x /opt/workshopandwater/start-workshopandwater.sh

WORKDIR /app
