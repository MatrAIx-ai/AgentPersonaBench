# syntax=docker/dockerfile:1.7
#
# SaturdaysBeachStage OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SaturdaysBeachStage native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SaturdaysBeachStage writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SaturdaysBeachStage app + its autostart launcher.
COPY saturdaysbeachstage.py /opt/saturdaysbeachstage/saturdaysbeachstage.py
COPY start-saturdaysbeachstage.sh /opt/saturdaysbeachstage/start-saturdaysbeachstage.sh
RUN chmod +x /opt/saturdaysbeachstage/start-saturdaysbeachstage.sh

WORKDIR /app
