# syntax=docker/dockerfile:1.7
#
# SupperAndSession OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperAndSession native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", SupperAndSession writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperAndSession app + its autostart launcher.
COPY supperandsession.py /opt/supperandsession/supperandsession.py
COPY start-supperandsession.sh /opt/supperandsession/start-supperandsession.sh
RUN chmod +x /opt/supperandsession/start-supperandsession.sh

WORKDIR /app
