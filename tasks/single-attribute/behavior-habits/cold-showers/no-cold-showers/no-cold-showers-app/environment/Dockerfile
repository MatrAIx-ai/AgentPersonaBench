# syntax=docker/dockerfile:1.7
#
# WarmWell OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WarmWell native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", WarmWell writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WarmWell app + its autostart launcher.
COPY warmwell.py /opt/warmwell/warmwell.py
COPY start-warmwell.sh /opt/warmwell/start-warmwell.sh
RUN chmod +x /opt/warmwell/start-warmwell.sh

WORKDIR /app
