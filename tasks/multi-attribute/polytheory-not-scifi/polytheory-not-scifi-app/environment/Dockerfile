# syntax=docker/dockerfile:1.7
#
# OpenLecturesWednesday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the OpenLecturesWednesday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Wednesdays", OpenLecturesWednesday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The OpenLecturesWednesday app + its autostart launcher.
COPY openlectureswednesday.py /opt/openlectureswednesday/openlectureswednesday.py
COPY start-openlectureswednesday.sh /opt/openlectureswednesday/start-openlectureswednesday.sh
RUN chmod +x /opt/openlectureswednesday/start-openlectureswednesday.sh

WORKDIR /app
