# syntax=docker/dockerfile:1.7
#
# TuneAndTome OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TuneAndTome native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", TuneAndTome writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TuneAndTome app + its autostart launcher.
COPY tuneandtome.py /opt/tuneandtome/tuneandtome.py
COPY start-tuneandtome.sh /opt/tuneandtome/start-tuneandtome.sh
RUN chmod +x /opt/tuneandtome/start-tuneandtome.sh

WORKDIR /app
