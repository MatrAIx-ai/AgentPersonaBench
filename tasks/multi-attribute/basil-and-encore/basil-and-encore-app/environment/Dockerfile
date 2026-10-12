# syntax=docker/dockerfile:1.7
#
# NightPlanner OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NightPlanner native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", NightPlanner writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NightPlanner app + its autostart launcher.
COPY nightplanner.py /opt/nightplanner/nightplanner.py
COPY start-nightplanner.sh /opt/nightplanner/start-nightplanner.sh
RUN chmod +x /opt/nightplanner/start-nightplanner.sh

WORKDIR /app
