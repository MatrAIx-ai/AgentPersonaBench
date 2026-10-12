# syntax=docker/dockerfile:1.7
#
# ScreenSupper OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenSupper native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book deals", ScreenSupper writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenSupper app + its autostart launcher.
COPY screensupper.py /opt/screensupper/screensupper.py
COPY start-screensupper.sh /opt/screensupper/start-screensupper.sh
RUN chmod +x /opt/screensupper/start-screensupper.sh

WORKDIR /app
