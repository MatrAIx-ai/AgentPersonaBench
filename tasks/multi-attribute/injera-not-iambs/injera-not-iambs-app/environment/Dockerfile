# syntax=docker/dockerfile:1.7
#
# AfterSupper OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the AfterSupper native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", AfterSupper writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The AfterSupper app + its autostart launcher.
COPY aftersupper.py /opt/aftersupper/aftersupper.py
COPY start-aftersupper.sh /opt/aftersupper/start-aftersupper.sh
RUN chmod +x /opt/aftersupper/start-aftersupper.sh

WORKDIR /app
