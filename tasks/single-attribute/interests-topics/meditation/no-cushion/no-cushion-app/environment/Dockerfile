# syntax=docker/dockerfile:1.7
#
# GymRecover OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GymRecover native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book sessions", GymRecover writes /app/output/sessions.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GymRecover app + its autostart launcher.
COPY gymrecover.py /opt/gymrecover/gymrecover.py
COPY start-gymrecover.sh /opt/gymrecover/start-gymrecover.sh
RUN chmod +x /opt/gymrecover/start-gymrecover.sh

WORKDIR /app
