# syntax=docker/dockerfile:1.7
#
# LunchAndRange OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LunchAndRange native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", LunchAndRange writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LunchAndRange app + its autostart launcher.
COPY lunchandrange.py /opt/lunchandrange/lunchandrange.py
COPY start-lunchandrange.sh /opt/lunchandrange/start-lunchandrange.sh
RUN chmod +x /opt/lunchandrange/start-lunchandrange.sh

WORKDIR /app
