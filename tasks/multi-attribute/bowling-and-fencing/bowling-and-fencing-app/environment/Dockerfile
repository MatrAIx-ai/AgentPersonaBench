# syntax=docker/dockerfile:1.7
#
# ArenaFridays OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ArenaFridays native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Fridays", ArenaFridays writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ArenaFridays app + its autostart launcher.
COPY arenafridays.py /opt/arenafridays/arenafridays.py
COPY start-arenafridays.sh /opt/arenafridays/start-arenafridays.sh
RUN chmod +x /opt/arenafridays/start-arenafridays.sh

WORKDIR /app
