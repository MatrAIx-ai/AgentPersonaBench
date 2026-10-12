# syntax=docker/dockerfile:1.7
#
# SupperAndChapter OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperAndChapter native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", SupperAndChapter writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperAndChapter app + its autostart launcher.
COPY supperandchapter.py /opt/supperandchapter/supperandchapter.py
COPY start-supperandchapter.sh /opt/supperandchapter/start-supperandchapter.sh
RUN chmod +x /opt/supperandchapter/start-supperandchapter.sh

WORKDIR /app
