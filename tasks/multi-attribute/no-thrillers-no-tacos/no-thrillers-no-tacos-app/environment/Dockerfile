# syntax=docker/dockerfile:1.7
#
# BoardAndBook OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BoardAndBook native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", BoardAndBook writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BoardAndBook app + its autostart launcher.
COPY boardandbook.py /opt/boardandbook/boardandbook.py
COPY start-boardandbook.sh /opt/boardandbook/start-boardandbook.sh
RUN chmod +x /opt/boardandbook/start-boardandbook.sh

WORKDIR /app
