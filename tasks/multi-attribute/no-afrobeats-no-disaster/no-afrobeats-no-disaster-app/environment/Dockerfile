# syntax=docker/dockerfile:1.7
#
# LateAndGig OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LateAndGig native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book nights", LateAndGig writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LateAndGig app + its autostart launcher.
COPY lateandgig.py /opt/lateandgig/lateandgig.py
COPY start-lateandgig.sh /opt/lateandgig/start-lateandgig.sh
RUN chmod +x /opt/lateandgig/start-lateandgig.sh

WORKDIR /app
