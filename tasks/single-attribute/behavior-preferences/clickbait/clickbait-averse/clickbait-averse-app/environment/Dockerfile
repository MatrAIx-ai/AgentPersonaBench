# syntax=docker/dockerfile:1.7
#
# Newsstand OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Newsstand native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Newsstand writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Newsstand app + its autostart launcher.
COPY newsstand.py /opt/newsstand/newsstand.py
COPY start-newsstand.sh /opt/newsstand/start-newsstand.sh
RUN chmod +x /opt/newsstand/start-newsstand.sh

WORKDIR /app
