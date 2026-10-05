# syntax=docker/dockerfile:1.7
#
# OpenLecturesThursday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the OpenLecturesThursday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", OpenLecturesThursday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The OpenLecturesThursday app + its autostart launcher.
COPY openlecturesthursday.py /opt/openlecturesthursday/openlecturesthursday.py
COPY start-openlecturesthursday.sh /opt/openlecturesthursday/start-openlecturesthursday.sh
RUN chmod +x /opt/openlecturesthursday/start-openlecturesthursday.sh

WORKDIR /app
