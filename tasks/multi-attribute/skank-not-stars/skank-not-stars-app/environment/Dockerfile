# syntax=docker/dockerfile:1.7
#
# AfterAndGig OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the AfterAndGig native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Fridays", AfterAndGig writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The AfterAndGig app + its autostart launcher.
COPY afterandgig.py /opt/afterandgig/afterandgig.py
COPY start-afterandgig.sh /opt/afterandgig/start-afterandgig.sh
RUN chmod +x /opt/afterandgig/start-afterandgig.sh

WORKDIR /app
