# syntax=docker/dockerfile:1.7
#
# SupperChapter OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperChapter native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", SupperChapter writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperChapter app + its autostart launcher.
COPY supperchapter.py /opt/supperchapter/supperchapter.py
COPY start-supperchapter.sh /opt/supperchapter/start-supperchapter.sh
RUN chmod +x /opt/supperchapter/start-supperchapter.sh

WORKDIR /app
