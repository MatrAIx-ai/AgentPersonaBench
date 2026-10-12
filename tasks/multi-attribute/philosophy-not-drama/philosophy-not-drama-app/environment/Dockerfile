# syntax=docker/dockerfile:1.7
#
# LecturesMonday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LecturesMonday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Mondays", LecturesMonday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LecturesMonday app + its autostart launcher.
COPY lecturesmonday.py /opt/lecturesmonday/lecturesmonday.py
COPY start-lecturesmonday.sh /opt/lecturesmonday/start-lecturesmonday.sh
RUN chmod +x /opt/lecturesmonday/start-lecturesmonday.sh

WORKDIR /app
