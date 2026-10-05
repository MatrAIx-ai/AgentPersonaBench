# syntax=docker/dockerfile:1.7
#
# SupportersWeekends OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupportersWeekends native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Weekends", SupportersWeekends writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupportersWeekends app + its autostart launcher.
COPY supportersweekends.py /opt/supportersweekends/supportersweekends.py
COPY start-supportersweekends.sh /opt/supportersweekends/start-supportersweekends.sh
RUN chmod +x /opt/supportersweekends/start-supportersweekends.sh

WORKDIR /app
