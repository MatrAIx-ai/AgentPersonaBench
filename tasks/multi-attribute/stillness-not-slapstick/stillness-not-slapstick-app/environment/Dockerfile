# syntax=docker/dockerfile:1.7
#
# HallSunday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HallSunday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", HallSunday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HallSunday app + its autostart launcher.
COPY hallsunday.py /opt/hallsunday/hallsunday.py
COPY start-hallsunday.sh /opt/hallsunday/start-hallsunday.sh
RUN chmod +x /opt/hallsunday/start-hallsunday.sh

WORKDIR /app
