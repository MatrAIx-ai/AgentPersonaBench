# syntax=docker/dockerfile:1.7
#
# SupperAndLive OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperAndLive native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", SupperAndLive writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperAndLive app + its autostart launcher.
COPY supperandlive.py /opt/supperandlive/supperandlive.py
COPY start-supperandlive.sh /opt/supperandlive/start-supperandlive.sh
RUN chmod +x /opt/supperandlive/start-supperandlive.sh

WORKDIR /app
