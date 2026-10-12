# syntax=docker/dockerfile:1.7
#
# SundayBundlesClub OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SundayBundlesClub native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SundayBundlesClub writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SundayBundlesClub app + its autostart launcher.
COPY sundaybundlesclub.py /opt/sundaybundlesclub/sundaybundlesclub.py
COPY start-sundaybundlesclub.sh /opt/sundaybundlesclub/start-sundaybundlesclub.sh
RUN chmod +x /opt/sundaybundlesclub/start-sundaybundlesclub.sh

WORKDIR /app
