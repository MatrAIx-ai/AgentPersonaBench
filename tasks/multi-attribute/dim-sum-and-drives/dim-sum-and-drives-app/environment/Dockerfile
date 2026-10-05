# syntax=docker/dockerfile:1.7
#
# NightsCentre OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NightsCentre native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", NightsCentre writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NightsCentre app + its autostart launcher.
COPY nightscentre.py /opt/nightscentre/nightscentre.py
COPY start-nightscentre.sh /opt/nightscentre/start-nightscentre.sh
RUN chmod +x /opt/nightscentre/start-nightscentre.sh

WORKDIR /app
