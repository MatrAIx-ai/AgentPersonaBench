# syntax=docker/dockerfile:1.7
#
# LaunchPass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LaunchPass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", LaunchPass writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LaunchPass app + its autostart launcher.
COPY launchpass.py /opt/launchpass/launchpass.py
COPY start-launchpass.sh /opt/launchpass/start-launchpass.sh
RUN chmod +x /opt/launchpass/start-launchpass.sh

WORKDIR /app
