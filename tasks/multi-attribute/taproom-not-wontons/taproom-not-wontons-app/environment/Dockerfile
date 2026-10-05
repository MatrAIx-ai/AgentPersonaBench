# syntax=docker/dockerfile:1.7
#
# TableAndTasting OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TableAndTasting native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", TableAndTasting writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TableAndTasting app + its autostart launcher.
COPY tableandtasting.py /opt/tableandtasting/tableandtasting.py
COPY start-tableandtasting.sh /opt/tableandtasting/start-tableandtasting.sh
RUN chmod +x /opt/tableandtasting/start-tableandtasting.sh

WORKDIR /app
