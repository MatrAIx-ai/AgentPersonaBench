# syntax=docker/dockerfile:1.7
#
# LecturesWednesday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LecturesWednesday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Wednesdays", LecturesWednesday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LecturesWednesday app + its autostart launcher.
COPY lectureswednesday.py /opt/lectureswednesday/lectureswednesday.py
COPY start-lectureswednesday.sh /opt/lectureswednesday/start-lectureswednesday.sh
RUN chmod +x /opt/lectureswednesday/start-lectureswednesday.sh

WORKDIR /app
