# syntax=docker/dockerfile:1.7
#
# MembersClubWeekends OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MembersClubWeekends native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Weekends", MembersClubWeekends writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MembersClubWeekends app + its autostart launcher.
COPY membersclubweekends.py /opt/membersclubweekends/membersclubweekends.py
COPY start-membersclubweekends.sh /opt/membersclubweekends/start-membersclubweekends.sh
RUN chmod +x /opt/membersclubweekends/start-membersclubweekends.sh

WORKDIR /app
