# syntax=docker/dockerfile:1.7
#
# SaturdaysLibrary OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysLibrary native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysLibrary writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysLibrary app + its autostart launcher.
COPY saturdayslibrary.py /opt/saturdayslibrary/saturdayslibrary.py
COPY start-saturdayslibrary.sh /opt/saturdayslibrary/start-saturdayslibrary.sh
RUN chmod +x /opt/saturdayslibrary/start-saturdayslibrary.sh

WORKDIR /app
