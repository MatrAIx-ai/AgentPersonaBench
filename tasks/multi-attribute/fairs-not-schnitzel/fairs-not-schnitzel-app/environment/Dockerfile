# syntax=docker/dockerfile:1.7
#
# SaturdaysCityCard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysCityCard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysCityCard writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysCityCard app + its autostart launcher.
COPY saturdayscitycard.py /opt/saturdayscitycard/saturdayscitycard.py
COPY start-saturdayscitycard.sh /opt/saturdayscitycard/start-saturdayscitycard.sh
RUN chmod +x /opt/saturdayscitycard/start-saturdayscitycard.sh

WORKDIR /app
