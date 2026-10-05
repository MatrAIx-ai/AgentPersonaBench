# syntax=docker/dockerfile:1.7
#
# BookAndMorning OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BookAndMorning native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", BookAndMorning writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BookAndMorning app + its autostart launcher.
COPY bookandmorning.py /opt/bookandmorning/bookandmorning.py
COPY start-bookandmorning.sh /opt/bookandmorning/start-bookandmorning.sh
RUN chmod +x /opt/bookandmorning/start-bookandmorning.sh

WORKDIR /app
