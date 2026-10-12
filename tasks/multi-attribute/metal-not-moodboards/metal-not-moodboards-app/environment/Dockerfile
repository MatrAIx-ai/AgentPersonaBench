# syntax=docker/dockerfile:1.7
#
# StageAndSession OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StageAndSession native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", StageAndSession writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StageAndSession app + its autostart launcher.
COPY stageandsession.py /opt/stageandsession/stageandsession.py
COPY start-stageandsession.sh /opt/stageandsession/start-stageandsession.sh
RUN chmod +x /opt/stageandsession/start-stageandsession.sh

WORKDIR /app
