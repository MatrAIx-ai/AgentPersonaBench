# syntax=docker/dockerfile:1.7
#
# ScreenAndBench OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenAndBench native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ScreenAndBench writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenAndBench app + its autostart launcher.
COPY screenandbench.py /opt/screenandbench/screenandbench.py
COPY start-screenandbench.sh /opt/screenandbench/start-screenandbench.sh
RUN chmod +x /opt/screenandbench/start-screenandbench.sh

WORKDIR /app
