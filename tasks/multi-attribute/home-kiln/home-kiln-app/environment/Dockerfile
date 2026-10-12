# syntax=docker/dockerfile:1.7
#
# LeaveWeeks OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LeaveWeeks native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book courses", LeaveWeeks writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LeaveWeeks app + its autostart launcher.
COPY leaveweeks.py /opt/leaveweeks/leaveweeks.py
COPY start-leaveweeks.sh /opt/leaveweeks/start-leaveweeks.sh
RUN chmod +x /opt/leaveweeks/start-leaveweeks.sh

WORKDIR /app
