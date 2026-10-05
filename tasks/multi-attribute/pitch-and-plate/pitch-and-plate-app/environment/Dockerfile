# syntax=docker/dockerfile:1.7
#
# SquadSunday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SquadSunday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SquadSunday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SquadSunday app + its autostart launcher.
COPY squadsunday.py /opt/squadsunday/squadsunday.py
COPY start-squadsunday.sh /opt/squadsunday/start-squadsunday.sh
RUN chmod +x /opt/squadsunday/start-squadsunday.sh

WORKDIR /app
