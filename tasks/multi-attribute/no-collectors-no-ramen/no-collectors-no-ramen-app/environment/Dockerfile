# syntax=docker/dockerfile:1.7
#
# LunchAndMorning OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LunchAndMorning native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", LunchAndMorning writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LunchAndMorning app + its autostart launcher.
COPY lunchandmorning.py /opt/lunchandmorning/lunchandmorning.py
COPY start-lunchandmorning.sh /opt/lunchandmorning/start-lunchandmorning.sh
RUN chmod +x /opt/lunchandmorning/start-lunchandmorning.sh

WORKDIR /app
