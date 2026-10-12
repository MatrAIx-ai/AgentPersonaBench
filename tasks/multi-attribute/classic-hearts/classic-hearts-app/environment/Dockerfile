# syntax=docker/dockerfile:1.7
#
# ScreenClub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenClub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book screenings", ScreenClub writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenClub app + its autostart launcher.
COPY screenclub.py /opt/screenclub/screenclub.py
COPY start-screenclub.sh /opt/screenclub/start-screenclub.sh
RUN chmod +x /opt/screenclub/start-screenclub.sh

WORKDIR /app
