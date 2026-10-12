# syntax=docker/dockerfile:1.7
#
# HandsOnHall OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HandsOnHall native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Claim sessions", HandsOnHall writes /app/output/handling.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HandsOnHall app + its autostart launcher.
COPY handsonhall.py /opt/handsonhall/handsonhall.py
COPY start-handsonhall.sh /opt/handsonhall/start-handsonhall.sh
RUN chmod +x /opt/handsonhall/start-handsonhall.sh

WORKDIR /app
