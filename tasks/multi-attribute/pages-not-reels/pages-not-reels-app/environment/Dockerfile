# syntax=docker/dockerfile:1.7
#
# EveningsFestival OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the EveningsFestival native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book evenings", EveningsFestival writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The EveningsFestival app + its autostart launcher.
COPY eveningsfestival.py /opt/eveningsfestival/eveningsfestival.py
COPY start-eveningsfestival.sh /opt/eveningsfestival/start-eveningsfestival.sh
RUN chmod +x /opt/eveningsfestival/start-eveningsfestival.sh

WORKDIR /app
