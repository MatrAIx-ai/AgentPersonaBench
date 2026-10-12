# syntax=docker/dockerfile:1.7
#
# NovelSupper OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NovelSupper native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book pairings", NovelSupper writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NovelSupper app + its autostart launcher.
COPY novelsupper.py /opt/novelsupper/novelsupper.py
COPY start-novelsupper.sh /opt/novelsupper/start-novelsupper.sh
RUN chmod +x /opt/novelsupper/start-novelsupper.sh

WORKDIR /app
