# syntax=docker/dockerfile:1.7
#
# WednesdaysUnion OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WednesdaysUnion native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Wednesdays", WednesdaysUnion writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WednesdaysUnion app + its autostart launcher.
COPY wednesdaysunion.py /opt/wednesdaysunion/wednesdaysunion.py
COPY start-wednesdaysunion.sh /opt/wednesdaysunion/start-wednesdaysunion.sh
RUN chmod +x /opt/wednesdaysunion/start-wednesdaysunion.sh

WORKDIR /app
