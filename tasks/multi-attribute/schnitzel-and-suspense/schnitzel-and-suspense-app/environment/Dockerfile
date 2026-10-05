# syntax=docker/dockerfile:1.7
#
# SupperCinema OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SupperCinema native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", SupperCinema writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SupperCinema app + its autostart launcher.
COPY suppercinema.py /opt/suppercinema/suppercinema.py
COPY start-suppercinema.sh /opt/suppercinema/start-suppercinema.sh
RUN chmod +x /opt/suppercinema/start-suppercinema.sh

WORKDIR /app
