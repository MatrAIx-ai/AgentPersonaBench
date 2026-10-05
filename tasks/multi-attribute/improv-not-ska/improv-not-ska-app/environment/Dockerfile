# syntax=docker/dockerfile:1.7
#
# HeadlinerAndHour OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HeadlinerAndHour native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Fridays", HeadlinerAndHour writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HeadlinerAndHour app + its autostart launcher.
COPY headlinerandhour.py /opt/headlinerandhour/headlinerandhour.py
COPY start-headlinerandhour.sh /opt/headlinerandhour/start-headlinerandhour.sh
RUN chmod +x /opt/headlinerandhour/start-headlinerandhour.sh

WORKDIR /app
