# syntax=docker/dockerfile:1.7
#
# MembersMonthSport OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MembersMonthSport native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Double-Headers", MembersMonthSport writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MembersMonthSport app + its autostart launcher.
COPY membersmonthsport.py /opt/membersmonthsport/membersmonthsport.py
COPY start-membersmonthsport.sh /opt/membersmonthsport/start-membersmonthsport.sh
RUN chmod +x /opt/membersmonthsport/start-membersmonthsport.sh

WORKDIR /app
