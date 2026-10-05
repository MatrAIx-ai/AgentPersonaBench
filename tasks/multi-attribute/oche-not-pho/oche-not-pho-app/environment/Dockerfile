# syntax=docker/dockerfile:1.7
#
# TableAndOche OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TableAndOche native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Fridays", TableAndOche writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TableAndOche app + its autostart launcher.
COPY tableandoche.py /opt/tableandoche/tableandoche.py
COPY start-tableandoche.sh /opt/tableandoche/start-tableandoche.sh
RUN chmod +x /opt/tableandoche/start-tableandoche.sh

WORKDIR /app
