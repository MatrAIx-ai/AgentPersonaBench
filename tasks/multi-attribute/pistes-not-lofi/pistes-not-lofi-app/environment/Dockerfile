# syntax=docker/dockerfile:1.7
#
# DayPassesPeak OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DayPassesPeak native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book day passes", DayPassesPeak writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DayPassesPeak app + its autostart launcher.
COPY daypassespeak.py /opt/daypassespeak/daypassespeak.py
COPY start-daypassespeak.sh /opt/daypassespeak/start-daypassespeak.sh
RUN chmod +x /opt/daypassespeak/start-daypassespeak.sh

WORKDIR /app
