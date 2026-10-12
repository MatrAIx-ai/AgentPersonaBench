# syntax=docker/dockerfile:1.7
#
# CardWeekend OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CardWeekend native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", CardWeekend writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CardWeekend app + its autostart launcher.
COPY cardweekend.py /opt/cardweekend/cardweekend.py
COPY start-cardweekend.sh /opt/cardweekend/start-cardweekend.sh
RUN chmod +x /opt/cardweekend/start-cardweekend.sh

WORKDIR /app
