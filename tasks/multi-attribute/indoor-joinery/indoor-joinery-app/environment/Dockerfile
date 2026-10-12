# syntax=docker/dockerfile:1.7
#
# BenchBooker OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BenchBooker native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", BenchBooker writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BenchBooker app + its autostart launcher.
COPY benchbooker.py /opt/benchbooker/benchbooker.py
COPY start-benchbooker.sh /opt/benchbooker/start-benchbooker.sh
RUN chmod +x /opt/benchbooker/start-benchbooker.sh

WORKDIR /app
