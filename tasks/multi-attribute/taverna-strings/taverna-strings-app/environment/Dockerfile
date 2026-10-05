# syntax=docker/dockerfile:1.7
#
# SupperSeason OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperSeason native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", SupperSeason writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperSeason app + its autostart launcher.
COPY supperseason.py /opt/supperseason/supperseason.py
COPY start-supperseason.sh /opt/supperseason/start-supperseason.sh
RUN chmod +x /opt/supperseason/start-supperseason.sh

WORKDIR /app
