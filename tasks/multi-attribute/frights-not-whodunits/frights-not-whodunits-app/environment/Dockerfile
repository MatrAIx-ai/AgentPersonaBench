# syntax=docker/dockerfile:1.7
#
# ScreenChapter OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ScreenChapter native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book bundles", ScreenChapter writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ScreenChapter app + its autostart launcher.
COPY screenchapter.py /opt/screenchapter/screenchapter.py
COPY start-screenchapter.sh /opt/screenchapter/start-screenchapter.sh
RUN chmod +x /opt/screenchapter/start-screenchapter.sh

WORKDIR /app
