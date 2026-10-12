# syntax=docker/dockerfile:1.7
#
# SpineAndScreen OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SpineAndScreen native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", SpineAndScreen writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SpineAndScreen app + its autostart launcher.
COPY spineandscreen.py /opt/spineandscreen/spineandscreen.py
COPY start-spineandscreen.sh /opt/spineandscreen/start-spineandscreen.sh
RUN chmod +x /opt/spineandscreen/start-spineandscreen.sh

WORKDIR /app
