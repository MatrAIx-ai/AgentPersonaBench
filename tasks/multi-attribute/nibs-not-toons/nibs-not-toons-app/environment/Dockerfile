# syntax=docker/dockerfile:1.7
#
# ScreenAndInk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenAndInk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ScreenAndInk writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenAndInk app + its autostart launcher.
COPY screenandink.py /opt/screenandink/screenandink.py
COPY start-screenandink.sh /opt/screenandink/start-screenandink.sh
RUN chmod +x /opt/screenandink/start-screenandink.sh

WORKDIR /app
