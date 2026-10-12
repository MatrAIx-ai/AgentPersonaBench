# syntax=docker/dockerfile:1.7
#
# DaysCityBreak OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DaysCityBreak native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book days", DaysCityBreak writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DaysCityBreak app + its autostart launcher.
COPY dayscitybreak.py /opt/dayscitybreak/dayscitybreak.py
COPY start-dayscitybreak.sh /opt/dayscitybreak/start-dayscitybreak.sh
RUN chmod +x /opt/dayscitybreak/start-dayscitybreak.sh

WORKDIR /app
