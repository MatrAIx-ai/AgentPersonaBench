# syntax=docker/dockerfile:1.7
#
# NightsSupperScreen OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NightsSupperScreen native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", NightsSupperScreen writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NightsSupperScreen app + its autostart launcher.
COPY nightssupperscreen.py /opt/nightssupperscreen/nightssupperscreen.py
COPY start-nightssupperscreen.sh /opt/nightssupperscreen/start-nightssupperscreen.sh
RUN chmod +x /opt/nightssupperscreen/start-nightssupperscreen.sh

WORKDIR /app
