# syntax=docker/dockerfile:1.7
#
# SundaysKitchen OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SundaysKitchen native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SundaysKitchen writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SundaysKitchen app + its autostart launcher.
COPY sundayskitchen.py /opt/sundayskitchen/sundayskitchen.py
COPY start-sundayskitchen.sh /opt/sundayskitchen/start-sundayskitchen.sh
RUN chmod +x /opt/sundayskitchen/start-sundayskitchen.sh

WORKDIR /app
