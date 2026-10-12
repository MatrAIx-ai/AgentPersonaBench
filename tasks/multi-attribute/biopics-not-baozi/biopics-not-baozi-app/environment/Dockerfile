# syntax=docker/dockerfile:1.7
#
# ReelAndTable OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ReelAndTable native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", ReelAndTable writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ReelAndTable app + its autostart launcher.
COPY reelandtable.py /opt/reelandtable/reelandtable.py
COPY start-reelandtable.sh /opt/reelandtable/start-reelandtable.sh
RUN chmod +x /opt/reelandtable/start-reelandtable.sh

WORKDIR /app
