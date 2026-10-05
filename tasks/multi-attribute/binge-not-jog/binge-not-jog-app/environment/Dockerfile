# syntax=docker/dockerfile:1.7
#
# ClubWeekend OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClubWeekend native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book weekends", ClubWeekend writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClubWeekend app + its autostart launcher.
COPY clubweekend.py /opt/clubweekend/clubweekend.py
COPY start-clubweekend.sh /opt/clubweekend/start-clubweekend.sh
RUN chmod +x /opt/clubweekend/start-clubweekend.sh

WORKDIR /app
