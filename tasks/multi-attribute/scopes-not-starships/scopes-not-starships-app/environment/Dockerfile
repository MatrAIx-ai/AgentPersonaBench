# syntax=docker/dockerfile:1.7
#
# NightsScienceCentre OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NightsScienceCentre native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", NightsScienceCentre writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NightsScienceCentre app + its autostart launcher.
COPY nightssciencecentre.py /opt/nightssciencecentre/nightssciencecentre.py
COPY start-nightssciencecentre.sh /opt/nightssciencecentre/start-nightssciencecentre.sh
RUN chmod +x /opt/nightssciencecentre/start-nightssciencecentre.sh

WORKDIR /app
