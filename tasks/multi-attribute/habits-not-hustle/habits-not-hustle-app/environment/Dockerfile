# syntax=docker/dockerfile:1.7
#
# TalkAndBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TalkAndBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", TalkAndBook writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TalkAndBook app + its autostart launcher.
COPY talkandbook.py /opt/talkandbook/talkandbook.py
COPY start-talkandbook.sh /opt/talkandbook/start-talkandbook.sh
RUN chmod +x /opt/talkandbook/start-talkandbook.sh

WORKDIR /app
