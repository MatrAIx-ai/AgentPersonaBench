# syntax=docker/dockerfile:1.7
#
# SundaysLakeside OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SundaysLakeside native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SundaysLakeside writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SundaysLakeside app + its autostart launcher.
COPY sundayslakeside.py /opt/sundayslakeside/sundayslakeside.py
COPY start-sundayslakeside.sh /opt/sundayslakeside/start-sundayslakeside.sh
RUN chmod +x /opt/sundayslakeside/start-sundayslakeside.sh

WORKDIR /app
