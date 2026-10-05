# syntax=docker/dockerfile:1.7
#
# FanSaturdays OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FanSaturdays native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", FanSaturdays writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FanSaturdays app + its autostart launcher.
COPY fansaturdays.py /opt/fansaturdays/fansaturdays.py
COPY start-fansaturdays.sh /opt/fansaturdays/start-fansaturdays.sh
RUN chmod +x /opt/fansaturdays/start-fansaturdays.sh

WORKDIR /app
