# syntax=docker/dockerfile:1.7
#
# LetFinder OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LetFinder native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book cottages", LetFinder writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LetFinder app + its autostart launcher.
COPY letfinder.py /opt/letfinder/letfinder.py
COPY start-letfinder.sh /opt/letfinder/start-letfinder.sh
RUN chmod +x /opt/letfinder/start-letfinder.sh

WORKDIR /app
