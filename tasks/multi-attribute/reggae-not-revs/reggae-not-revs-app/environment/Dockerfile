# syntax=docker/dockerfile:1.7
#
# SaturdaysShowground OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysShowground native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysShowground writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysShowground app + its autostart launcher.
COPY saturdaysshowground.py /opt/saturdaysshowground/saturdaysshowground.py
COPY start-saturdaysshowground.sh /opt/saturdaysshowground/start-saturdaysshowground.sh
RUN chmod +x /opt/saturdaysshowground/start-saturdaysshowground.sh

WORKDIR /app
