# syntax=docker/dockerfile:1.7
#
# ScreenAndHide OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenAndHide native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ScreenAndHide writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenAndHide app + its autostart launcher.
COPY screenandhide.py /opt/screenandhide/screenandhide.py
COPY start-screenandhide.sh /opt/screenandhide/start-screenandhide.sh
RUN chmod +x /opt/screenandhide/start-screenandhide.sh

WORKDIR /app
