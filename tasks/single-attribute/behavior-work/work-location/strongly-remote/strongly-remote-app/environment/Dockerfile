# syntax=docker/dockerfile:1.7
#
# WeekDock OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WeekDock native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book week", WeekDock writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WeekDock app + its autostart launcher.
COPY weekdock.py /opt/weekdock/weekdock.py
COPY start-weekdock.sh /opt/weekdock/start-weekdock.sh
RUN chmod +x /opt/weekdock/start-weekdock.sh

WORKDIR /app
