# syntax=docker/dockerfile:1.7
#
# DaysFair OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DaysFair native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book pairs", DaysFair writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DaysFair app + its autostart launcher.
COPY daysfair.py /opt/daysfair/daysfair.py
COPY start-daysfair.sh /opt/daysfair/start-daysfair.sh
RUN chmod +x /opt/daysfair/start-daysfair.sh

WORKDIR /app
