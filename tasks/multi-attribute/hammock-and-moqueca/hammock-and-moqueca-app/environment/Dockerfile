# syntax=docker/dockerfile:1.7
#
# WeekAway OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WeekAway native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book packages", WeekAway writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WeekAway app + its autostart launcher.
COPY weekaway.py /opt/weekaway/weekaway.py
COPY start-weekaway.sh /opt/weekaway/start-weekaway.sh
RUN chmod +x /opt/weekaway/start-weekaway.sh

WORKDIR /app
