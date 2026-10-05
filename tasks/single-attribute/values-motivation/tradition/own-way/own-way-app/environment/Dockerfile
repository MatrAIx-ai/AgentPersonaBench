# syntax=docker/dockerfile:1.7
#
# EventBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the EventBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book elements", EventBook writes /app/output/booking.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EventBook app + its autostart launcher.
COPY eventbook.py /opt/eventbook/eventbook.py
COPY start-eventbook.sh /opt/eventbook/start-eventbook.sh
RUN chmod +x /opt/eventbook/start-eventbook.sh

WORKDIR /app
