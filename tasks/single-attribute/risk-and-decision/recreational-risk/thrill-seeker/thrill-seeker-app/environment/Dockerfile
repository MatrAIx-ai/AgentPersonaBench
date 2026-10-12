# syntax=docker/dockerfile:1.7
#
# RidgeBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the RidgeBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", RidgeBook writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The RidgeBook app + its autostart launcher.
COPY ridgebook.py /opt/ridgebook/ridgebook.py
COPY start-ridgebook.sh /opt/ridgebook/start-ridgebook.sh
RUN chmod +x /opt/ridgebook/start-ridgebook.sh

WORKDIR /app
