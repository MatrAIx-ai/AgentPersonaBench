# syntax=docker/dockerfile:1.7
#
# TalkAndMatch OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TalkAndMatch native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", TalkAndMatch writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TalkAndMatch app + its autostart launcher.
COPY talkandmatch.py /opt/talkandmatch/talkandmatch.py
COPY start-talkandmatch.sh /opt/talkandmatch/start-talkandmatch.sh
RUN chmod +x /opt/talkandmatch/start-talkandmatch.sh

WORKDIR /app
