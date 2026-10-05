# syntax=docker/dockerfile:1.7
#
# SaturdaysCity OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysCity native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysCity writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysCity app + its autostart launcher.
COPY saturdayscity.py /opt/saturdayscity/saturdayscity.py
COPY start-saturdayscity.sh /opt/saturdayscity/start-saturdayscity.sh
RUN chmod +x /opt/saturdayscity/start-saturdayscity.sh

WORKDIR /app
