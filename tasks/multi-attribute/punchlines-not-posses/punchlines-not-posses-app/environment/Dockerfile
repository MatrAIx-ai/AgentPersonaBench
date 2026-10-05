# syntax=docker/dockerfile:1.7
#
# EarlyAndLate OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the EarlyAndLate native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book passes", EarlyAndLate writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EarlyAndLate app + its autostart launcher.
COPY earlyandlate.py /opt/earlyandlate/earlyandlate.py
COPY start-earlyandlate.sh /opt/earlyandlate/start-earlyandlate.sh
RUN chmod +x /opt/earlyandlate/start-earlyandlate.sh

WORKDIR /app
