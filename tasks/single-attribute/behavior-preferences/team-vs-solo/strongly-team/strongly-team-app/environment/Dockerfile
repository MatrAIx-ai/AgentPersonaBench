# syntax=docker/dockerfile:1.7
#
# SeasonSeat OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SeasonSeat native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Sign up", SeasonSeat writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SeasonSeat app + its autostart launcher.
COPY seasonseat.py /opt/seasonseat/seasonseat.py
COPY start-seasonseat.sh /opt/seasonseat/start-seasonseat.sh
RUN chmod +x /opt/seasonseat/start-seasonseat.sh

WORKDIR /app
