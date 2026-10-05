# syntax=docker/dockerfile:1.7
#
# TalkSaturdaysLibrary OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TalkSaturdaysLibrary native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", TalkSaturdaysLibrary writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TalkSaturdaysLibrary app + its autostart launcher.
COPY talksaturdayslibrary.py /opt/talksaturdayslibrary/talksaturdayslibrary.py
COPY start-talksaturdayslibrary.sh /opt/talksaturdayslibrary/start-talksaturdayslibrary.sh
RUN chmod +x /opt/talksaturdayslibrary/start-talksaturdayslibrary.sh

WORKDIR /app
