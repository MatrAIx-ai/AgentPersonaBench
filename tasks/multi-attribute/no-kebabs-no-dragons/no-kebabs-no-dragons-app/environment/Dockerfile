# syntax=docker/dockerfile:1.7
#
# TomeAndTable OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TomeAndTable native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", TomeAndTable writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TomeAndTable app + its autostart launcher.
COPY tomeandtable.py /opt/tomeandtable/tomeandtable.py
COPY start-tomeandtable.sh /opt/tomeandtable/start-tomeandtable.sh
RUN chmod +x /opt/tomeandtable/start-tomeandtable.sh

WORKDIR /app
