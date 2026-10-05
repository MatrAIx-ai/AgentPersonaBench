# syntax=docker/dockerfile:1.7
#
# TableWeek OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TableWeek native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book tables", TableWeek writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TableWeek app + its autostart launcher.
COPY tableweek.py /opt/tableweek/tableweek.py
COPY start-tableweek.sh /opt/tableweek/start-tableweek.sh
RUN chmod +x /opt/tableweek/start-tableweek.sh

WORKDIR /app
