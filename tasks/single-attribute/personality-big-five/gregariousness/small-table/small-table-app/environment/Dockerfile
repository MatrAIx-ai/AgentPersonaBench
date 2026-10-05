# syntax=docker/dockerfile:1.7
#
# RetreatApp OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the RetreatApp native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", RetreatApp writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The RetreatApp app + its autostart launcher.
COPY retreatapp.py /opt/retreatapp/retreatapp.py
COPY start-retreatapp.sh /opt/retreatapp/start-retreatapp.sh
RUN chmod +x /opt/retreatapp/start-retreatapp.sh

WORKDIR /app
