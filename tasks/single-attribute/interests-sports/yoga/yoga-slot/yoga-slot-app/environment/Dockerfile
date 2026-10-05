# syntax=docker/dockerfile:1.7
#
# ClassBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ClassBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book classes", ClassBook writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ClassBook app + its autostart launcher.
COPY classbook.py /opt/classbook/classbook.py
COPY start-classbook.sh /opt/classbook/start-classbook.sh
RUN chmod +x /opt/classbook/start-classbook.sh

WORKDIR /app
