# syntax=docker/dockerfile:1.7
#
# ScreenAndChapter OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenAndChapter native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", ScreenAndChapter writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenAndChapter app + its autostart launcher.
COPY screenandchapter.py /opt/screenandchapter/screenandchapter.py
COPY start-screenandchapter.sh /opt/screenandchapter/start-screenandchapter.sh
RUN chmod +x /opt/screenandchapter/start-screenandchapter.sh

WORKDIR /app
