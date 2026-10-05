# syntax=docker/dockerfile:1.7
#
# WeekendDoubleHeader OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WeekendDoubleHeader native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Weekends", WeekendDoubleHeader writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WeekendDoubleHeader app + its autostart launcher.
COPY weekenddoubleheader.py /opt/weekenddoubleheader/weekenddoubleheader.py
COPY start-weekenddoubleheader.sh /opt/weekenddoubleheader/start-weekenddoubleheader.sh
RUN chmod +x /opt/weekenddoubleheader/start-weekenddoubleheader.sh

WORKDIR /app
