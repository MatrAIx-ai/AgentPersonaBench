# syntax=docker/dockerfile:1.7
#
# PassFest OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PassFest native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book screenings", PassFest writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PassFest app + its autostart launcher.
COPY passfest.py /opt/passfest/passfest.py
COPY start-passfest.sh /opt/passfest/start-passfest.sh
RUN chmod +x /opt/passfest/start-passfest.sh

WORKDIR /app
