# syntax=docker/dockerfile:1.7
#
# SaturdaysPark OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysPark native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysPark writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysPark app + its autostart launcher.
COPY saturdayspark.py /opt/saturdayspark/saturdayspark.py
COPY start-saturdayspark.sh /opt/saturdayspark/start-saturdayspark.sh
RUN chmod +x /opt/saturdayspark/start-saturdayspark.sh

WORKDIR /app
