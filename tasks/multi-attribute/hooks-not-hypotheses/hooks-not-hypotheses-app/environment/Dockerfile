# syntax=docker/dockerfile:1.7
#
# DaysArena OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DaysArena native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book passes", DaysArena writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DaysArena app + its autostart launcher.
COPY daysarena.py /opt/daysarena/daysarena.py
COPY start-daysarena.sh /opt/daysarena/start-daysarena.sh
RUN chmod +x /opt/daysarena/start-daysarena.sh

WORKDIR /app
