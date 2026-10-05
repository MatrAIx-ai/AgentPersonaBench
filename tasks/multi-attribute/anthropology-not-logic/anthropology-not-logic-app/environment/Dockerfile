# syntax=docker/dockerfile:1.7
#
# EveningTalksMuseum OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the EveningTalksMuseum native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book lates", EveningTalksMuseum writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EveningTalksMuseum app + its autostart launcher.
COPY eveningtalksmuseum.py /opt/eveningtalksmuseum/eveningtalksmuseum.py
COPY start-eveningtalksmuseum.sh /opt/eveningtalksmuseum/start-eveningtalksmuseum.sh
RUN chmod +x /opt/eveningtalksmuseum/start-eveningtalksmuseum.sh

WORKDIR /app
