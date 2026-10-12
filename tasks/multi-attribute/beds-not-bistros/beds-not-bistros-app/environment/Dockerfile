# syntax=docker/dockerfile:1.7
#
# ClubSaturdaysBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClubSaturdaysBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ClubSaturdaysBook writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClubSaturdaysBook app + its autostart launcher.
COPY clubsaturdaysbook.py /opt/clubsaturdaysbook/clubsaturdaysbook.py
COPY start-clubsaturdaysbook.sh /opt/clubsaturdaysbook/start-clubsaturdaysbook.sh
RUN chmod +x /opt/clubsaturdaysbook/start-clubsaturdaysbook.sh

WORKDIR /app
