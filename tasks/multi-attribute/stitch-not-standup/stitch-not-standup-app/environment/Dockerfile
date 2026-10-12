# syntax=docker/dockerfile:1.7
#
# DoubleFriday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DoubleFriday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Fridays", DoubleFriday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DoubleFriday app + its autostart launcher.
COPY doublefriday.py /opt/doublefriday/doublefriday.py
COPY start-doublefriday.sh /opt/doublefriday/start-doublefriday.sh
RUN chmod +x /opt/doublefriday/start-doublefriday.sh

WORKDIR /app
