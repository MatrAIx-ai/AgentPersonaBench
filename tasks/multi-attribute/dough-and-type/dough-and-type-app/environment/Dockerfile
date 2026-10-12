# syntax=docker/dockerfile:1.7
#
# MakersFair OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MakersFair native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book days", MakersFair writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MakersFair app + its autostart launcher.
COPY makersfair.py /opt/makersfair/makersfair.py
COPY start-makersfair.sh /opt/makersfair/start-makersfair.sh
RUN chmod +x /opt/makersfair/start-makersfair.sh

WORKDIR /app
