# syntax=docker/dockerfile:1.7
#
# ScreenPick OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenPick native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book screenings", ScreenPick writes /app/output/screenings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenPick app + its autostart launcher.
COPY screenpick.py /opt/screenpick/screenpick.py
COPY start-screenpick.sh /opt/screenpick/start-screenpick.sh
RUN chmod +x /opt/screenpick/start-screenpick.sh

WORKDIR /app
