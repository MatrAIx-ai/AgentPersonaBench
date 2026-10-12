# syntax=docker/dockerfile:1.7
#
# SundaysBarn OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SundaysBarn native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SundaysBarn writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SundaysBarn app + its autostart launcher.
COPY sundaysbarn.py /opt/sundaysbarn/sundaysbarn.py
COPY start-sundaysbarn.sh /opt/sundaysbarn/start-sundaysbarn.sh
RUN chmod +x /opt/sundaysbarn/start-sundaysbarn.sh

WORKDIR /app
