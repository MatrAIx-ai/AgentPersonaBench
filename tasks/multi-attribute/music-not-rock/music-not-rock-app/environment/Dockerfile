# syntax=docker/dockerfile:1.7
#
# EveningsTaster OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the EveningsTaster native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", EveningsTaster writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EveningsTaster app + its autostart launcher.
COPY eveningstaster.py /opt/eveningstaster/eveningstaster.py
COPY start-eveningstaster.sh /opt/eveningstaster/start-eveningstaster.sh
RUN chmod +x /opt/eveningstaster/start-eveningstaster.sh

WORKDIR /app
