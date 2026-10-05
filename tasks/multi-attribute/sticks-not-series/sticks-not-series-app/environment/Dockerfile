# syntax=docker/dockerfile:1.7
#
# SaturdaysClub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysClub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book pairs", SaturdaysClub writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysClub app + its autostart launcher.
COPY saturdaysclub.py /opt/saturdaysclub/saturdaysclub.py
COPY start-saturdaysclub.sh /opt/saturdaysclub/start-saturdaysclub.sh
RUN chmod +x /opt/saturdaysclub/start-saturdaysclub.sh

WORKDIR /app
