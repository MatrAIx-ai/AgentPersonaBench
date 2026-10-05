# syntax=docker/dockerfile:1.7
#
# SaturdaysHub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysHub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysHub writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysHub app + its autostart launcher.
COPY saturdayshub.py /opt/saturdayshub/saturdayshub.py
COPY start-saturdayshub.sh /opt/saturdayshub/start-saturdayshub.sh
RUN chmod +x /opt/saturdayshub/start-saturdayshub.sh

WORKDIR /app
