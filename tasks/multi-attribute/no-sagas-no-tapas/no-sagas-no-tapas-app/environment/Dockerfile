# syntax=docker/dockerfile:1.7
#
# EveningsSociety OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the EveningsSociety native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", EveningsSociety writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EveningsSociety app + its autostart launcher.
COPY eveningssociety.py /opt/eveningssociety/eveningssociety.py
COPY start-eveningssociety.sh /opt/eveningssociety/start-eveningssociety.sh
RUN chmod +x /opt/eveningssociety/start-eveningssociety.sh

WORKDIR /app
