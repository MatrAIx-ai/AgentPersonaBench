# syntax=docker/dockerfile:1.7
#
# ScienceTalksSunday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScienceTalksSunday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", ScienceTalksSunday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScienceTalksSunday app + its autostart launcher.
COPY sciencetalkssunday.py /opt/sciencetalkssunday/sciencetalkssunday.py
COPY start-sciencetalkssunday.sh /opt/sciencetalkssunday/start-sciencetalkssunday.sh
RUN chmod +x /opt/sciencetalkssunday/start-sciencetalkssunday.sh

WORKDIR /app
