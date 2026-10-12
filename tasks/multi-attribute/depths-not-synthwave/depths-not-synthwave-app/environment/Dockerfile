# syntax=docker/dockerfile:1.7
#
# BoathouseAndDive OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BoathouseAndDive native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", BoathouseAndDive writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BoathouseAndDive app + its autostart launcher.
COPY boathouseanddive.py /opt/boathouseanddive/boathouseanddive.py
COPY start-boathouseanddive.sh /opt/boathouseanddive/start-boathouseanddive.sh
RUN chmod +x /opt/boathouseanddive/start-boathouseanddive.sh

WORKDIR /app
