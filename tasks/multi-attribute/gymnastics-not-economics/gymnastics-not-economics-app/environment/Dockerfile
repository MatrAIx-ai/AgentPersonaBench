# syntax=docker/dockerfile:1.7
#
# TalkAndArena OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TalkAndArena native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", TalkAndArena writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TalkAndArena app + its autostart launcher.
COPY talkandarena.py /opt/talkandarena/talkandarena.py
COPY start-talkandarena.sh /opt/talkandarena/start-talkandarena.sh
RUN chmod +x /opt/talkandarena/start-talkandarena.sh

WORKDIR /app
