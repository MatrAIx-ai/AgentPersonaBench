# syntax=docker/dockerfile:1.7
#
# ShelfSaturdays OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ShelfSaturdays native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", ShelfSaturdays writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ShelfSaturdays app + its autostart launcher.
COPY shelfsaturdays.py /opt/shelfsaturdays/shelfsaturdays.py
COPY start-shelfsaturdays.sh /opt/shelfsaturdays/start-shelfsaturdays.sh
RUN chmod +x /opt/shelfsaturdays/start-shelfsaturdays.sh

WORKDIR /app
