# syntax=docker/dockerfile:1.7
#
# SaturdaysCircus OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysCircus native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysCircus writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysCircus app + its autostart launcher.
COPY saturdayscircus.py /opt/saturdayscircus/saturdayscircus.py
COPY start-saturdayscircus.sh /opt/saturdayscircus/start-saturdayscircus.sh
RUN chmod +x /opt/saturdayscircus/start-saturdayscircus.sh

WORKDIR /app
