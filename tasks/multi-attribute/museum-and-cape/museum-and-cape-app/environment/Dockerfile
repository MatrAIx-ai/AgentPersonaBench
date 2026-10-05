# syntax=docker/dockerfile:1.7
#
# WeekendPlanner OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WeekendPlanner native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book weekends", WeekendPlanner writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WeekendPlanner app + its autostart launcher.
COPY weekendplanner.py /opt/weekendplanner/weekendplanner.py
COPY start-weekendplanner.sh /opt/weekendplanner/start-weekendplanner.sh
RUN chmod +x /opt/weekendplanner/start-weekendplanner.sh

WORKDIR /app
