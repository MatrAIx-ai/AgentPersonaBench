# syntax=docker/dockerfile:1.7
#
# DayRetreat OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DayRetreat native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book days", DayRetreat writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DayRetreat app + its autostart launcher.
COPY dayretreat.py /opt/dayretreat/dayretreat.py
COPY start-dayretreat.sh /opt/dayretreat/start-dayretreat.sh
RUN chmod +x /opt/dayretreat/start-dayretreat.sh

WORKDIR /app
