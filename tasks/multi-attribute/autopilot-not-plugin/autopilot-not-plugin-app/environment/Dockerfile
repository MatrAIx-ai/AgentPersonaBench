# syntax=docker/dockerfile:1.7
#
# HireThreeWeek OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HireThreeWeek native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book cars", HireThreeWeek writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HireThreeWeek app + its autostart launcher.
COPY hirethreeweek.py /opt/hirethreeweek/hirethreeweek.py
COPY start-hirethreeweek.sh /opt/hirethreeweek/start-hirethreeweek.sh
RUN chmod +x /opt/hirethreeweek/start-hirethreeweek.sh

WORKDIR /app
