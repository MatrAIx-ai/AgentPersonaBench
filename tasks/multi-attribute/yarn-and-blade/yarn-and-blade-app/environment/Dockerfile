# syntax=docker/dockerfile:1.7
#
# NightMakers OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NightMakers native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", NightMakers writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NightMakers app + its autostart launcher.
COPY nightmakers.py /opt/nightmakers/nightmakers.py
COPY start-nightmakers.sh /opt/nightmakers/start-nightmakers.sh
RUN chmod +x /opt/nightmakers/start-nightmakers.sh

WORKDIR /app
