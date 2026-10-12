# syntax=docker/dockerfile:1.7
#
# CraftDays OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CraftDays native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book workshops", CraftDays writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CraftDays app + its autostart launcher.
COPY craftdays.py /opt/craftdays/craftdays.py
COPY start-craftdays.sh /opt/craftdays/start-craftdays.sh
RUN chmod +x /opt/craftdays/start-craftdays.sh

WORKDIR /app
