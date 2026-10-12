# syntax=docker/dockerfile:1.7
#
# BarnTicket OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BarnTicket native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", BarnTicket writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BarnTicket app + its autostart launcher.
COPY barnticket.py /opt/barnticket/barnticket.py
COPY start-barnticket.sh /opt/barnticket/start-barnticket.sh
RUN chmod +x /opt/barnticket/start-barnticket.sh

WORKDIR /app
