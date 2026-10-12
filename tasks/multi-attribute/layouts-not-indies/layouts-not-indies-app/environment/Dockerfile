# syntax=docker/dockerfile:1.7
#
# ScreenAndAlbum OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenAndAlbum native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ScreenAndAlbum writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenAndAlbum app + its autostart launcher.
COPY screenandalbum.py /opt/screenandalbum/screenandalbum.py
COPY start-screenandalbum.sh /opt/screenandalbum/start-screenandalbum.sh
RUN chmod +x /opt/screenandalbum/start-screenandalbum.sh

WORKDIR /app
