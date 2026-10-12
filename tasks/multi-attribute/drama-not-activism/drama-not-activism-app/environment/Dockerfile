# syntax=docker/dockerfile:1.7
#
# LecturesThursday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LecturesThursday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", LecturesThursday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LecturesThursday app + its autostart launcher.
COPY lecturesthursday.py /opt/lecturesthursday/lecturesthursday.py
COPY start-lecturesthursday.sh /opt/lecturesthursday/start-lecturesthursday.sh
RUN chmod +x /opt/lecturesthursday/start-lecturesthursday.sh

WORKDIR /app
