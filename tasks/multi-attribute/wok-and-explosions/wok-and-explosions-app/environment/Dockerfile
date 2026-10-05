# syntax=docker/dockerfile:1.7
#
# SupperReel OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperReel native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book deals", SupperReel writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperReel app + its autostart launcher.
COPY supperreel.py /opt/supperreel/supperreel.py
COPY start-supperreel.sh /opt/supperreel/start-supperreel.sh
RUN chmod +x /opt/supperreel/start-supperreel.sh

WORKDIR /app
