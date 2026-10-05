# syntax=docker/dockerfile:1.7
#
# CollegePairsEvening OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CollegePairsEvening native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", CollegePairsEvening writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CollegePairsEvening app + its autostart launcher.
COPY collegepairsevening.py /opt/collegepairsevening/collegepairsevening.py
COPY start-collegepairsevening.sh /opt/collegepairsevening/start-collegepairsevening.sh
RUN chmod +x /opt/collegepairsevening/start-collegepairsevening.sh

WORKDIR /app
