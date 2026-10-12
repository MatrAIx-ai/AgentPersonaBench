# syntax=docker/dockerfile:1.7
#
# WednesdaysHall OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WednesdaysHall native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Wednesdays", WednesdaysHall writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WednesdaysHall app + its autostart launcher.
COPY wednesdayshall.py /opt/wednesdayshall/wednesdayshall.py
COPY start-wednesdayshall.sh /opt/wednesdayshall/start-wednesdayshall.sh
RUN chmod +x /opt/wednesdayshall/start-wednesdayshall.sh

WORKDIR /app
