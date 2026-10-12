# syntax=docker/dockerfile:1.7
#
# SundaysGameAndTalk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SundaysGameAndTalk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SundaysGameAndTalk writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SundaysGameAndTalk app + its autostart launcher.
COPY sundaysgameandtalk.py /opt/sundaysgameandtalk/sundaysgameandtalk.py
COPY start-sundaysgameandtalk.sh /opt/sundaysgameandtalk/start-sundaysgameandtalk.sh
RUN chmod +x /opt/sundaysgameandtalk/start-sundaysgameandtalk.sh

WORKDIR /app
