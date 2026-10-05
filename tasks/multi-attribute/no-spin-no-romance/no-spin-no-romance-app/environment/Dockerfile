# syntax=docker/dockerfile:1.7
#
# ScreenSessionSunday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenSessionSunday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", ScreenSessionSunday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenSessionSunday app + its autostart launcher.
COPY screensessionsunday.py /opt/screensessionsunday/screensessionsunday.py
COPY start-screensessionsunday.sh /opt/screensessionsunday/start-screensessionsunday.sh
RUN chmod +x /opt/screensessionsunday/start-screensessionsunday.sh

WORKDIR /app
