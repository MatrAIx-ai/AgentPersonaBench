# syntax=docker/dockerfile:1.7
#
# SetsBrunch OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SetsBrunch native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book brunches", SetsBrunch writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SetsBrunch app + its autostart launcher.
COPY setsbrunch.py /opt/setsbrunch/setsbrunch.py
COPY start-setsbrunch.sh /opt/setsbrunch/start-setsbrunch.sh
RUN chmod +x /opt/setsbrunch/start-setsbrunch.sh

WORKDIR /app
