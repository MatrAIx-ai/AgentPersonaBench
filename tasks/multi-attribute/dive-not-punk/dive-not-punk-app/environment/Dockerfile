# syntax=docker/dockerfile:1.7
#
# SaturdaysBoathouse OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysBoathouse native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysBoathouse writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysBoathouse app + its autostart launcher.
COPY saturdaysboathouse.py /opt/saturdaysboathouse/saturdaysboathouse.py
COPY start-saturdaysboathouse.sh /opt/saturdaysboathouse/start-saturdaysboathouse.sh
RUN chmod +x /opt/saturdaysboathouse/start-saturdaysboathouse.sh

WORKDIR /app
