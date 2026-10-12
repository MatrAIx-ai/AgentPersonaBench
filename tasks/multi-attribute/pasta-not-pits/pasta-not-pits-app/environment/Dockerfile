# syntax=docker/dockerfile:1.7
#
# NightHall OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NightHall native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", NightHall writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NightHall app + its autostart launcher.
COPY nighthall.py /opt/nighthall/nighthall.py
COPY start-nighthall.sh /opt/nighthall/start-nighthall.sh
RUN chmod +x /opt/nighthall/start-nighthall.sh

WORKDIR /app
