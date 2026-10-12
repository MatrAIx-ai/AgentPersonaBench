# syntax=docker/dockerfile:1.7
#
# MeetupsMembers OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MeetupsMembers native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book meetups", MeetupsMembers writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MeetupsMembers app + its autostart launcher.
COPY meetupsmembers.py /opt/meetupsmembers/meetupsmembers.py
COPY start-meetupsmembers.sh /opt/meetupsmembers/start-meetupsmembers.sh
RUN chmod +x /opt/meetupsmembers/start-meetupsmembers.sh

WORKDIR /app
