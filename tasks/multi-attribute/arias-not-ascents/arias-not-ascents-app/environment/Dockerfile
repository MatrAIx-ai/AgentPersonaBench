# syntax=docker/dockerfile:1.7
#
# DaysBreak OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DaysBreak native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book packages", DaysBreak writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DaysBreak app + its autostart launcher.
COPY daysbreak.py /opt/daysbreak/daysbreak.py
COPY start-daysbreak.sh /opt/daysbreak/start-daysbreak.sh
RUN chmod +x /opt/daysbreak/start-daysbreak.sh

WORKDIR /app
