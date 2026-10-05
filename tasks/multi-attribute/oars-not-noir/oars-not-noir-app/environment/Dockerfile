# syntax=docker/dockerfile:1.7
#
# SundaysRiverside OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SundaysRiverside native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Sundays", SundaysRiverside writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SundaysRiverside app + its autostart launcher.
COPY sundaysriverside.py /opt/sundaysriverside/sundaysriverside.py
COPY start-sundaysriverside.sh /opt/sundaysriverside/start-sundaysriverside.sh
RUN chmod +x /opt/sundaysriverside/start-sundaysriverside.sh

WORKDIR /app
