# syntax=docker/dockerfile:1.7
#
# ReadAndMake OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ReadAndMake native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book meetups", ReadAndMake writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ReadAndMake app + its autostart launcher.
COPY readandmake.py /opt/readandmake/readandmake.py
COPY start-readandmake.sh /opt/readandmake/start-readandmake.sh
RUN chmod +x /opt/readandmake/start-readandmake.sh

WORKDIR /app
