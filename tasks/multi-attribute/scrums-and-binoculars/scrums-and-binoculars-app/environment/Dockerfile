# syntax=docker/dockerfile:1.7
#
# PairsWeekend OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PairsWeekend native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book pairs", PairsWeekend writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PairsWeekend app + its autostart launcher.
COPY pairsweekend.py /opt/pairsweekend/pairsweekend.py
COPY start-pairsweekend.sh /opt/pairsweekend/start-pairsweekend.sh
RUN chmod +x /opt/pairsweekend/start-pairsweekend.sh

WORKDIR /app
