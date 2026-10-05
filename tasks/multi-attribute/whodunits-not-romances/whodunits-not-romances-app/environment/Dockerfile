# syntax=docker/dockerfile:1.7
#
# ScreenAndPage OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenAndPage native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", ScreenAndPage writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenAndPage app + its autostart launcher.
COPY screenandpage.py /opt/screenandpage/screenandpage.py
COPY start-screenandpage.sh /opt/screenandpage/start-screenandpage.sh
RUN chmod +x /opt/screenandpage/start-screenandpage.sh

WORKDIR /app
