# syntax=docker/dockerfile:1.7
#
# WeekClub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WeekClub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book pairs", WeekClub writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WeekClub app + its autostart launcher.
COPY weekclub.py /opt/weekclub/weekclub.py
COPY start-weekclub.sh /opt/weekclub/start-weekclub.sh
RUN chmod +x /opt/weekclub/start-weekclub.sh

WORKDIR /app
