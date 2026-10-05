# syntax=docker/dockerfile:1.7
#
# TablesCafe OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TablesCafe native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", TablesCafe writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TablesCafe app + its autostart launcher.
COPY tablescafe.py /opt/tablescafe/tablescafe.py
COPY start-tablescafe.sh /opt/tablescafe/start-tablescafe.sh
RUN chmod +x /opt/tablescafe/start-tablescafe.sh

WORKDIR /app
