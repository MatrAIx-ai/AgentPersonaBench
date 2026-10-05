# syntax=docker/dockerfile:1.7
#
# DayPassesFestival OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DayPassesFestival native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book day passes", DayPassesFestival writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DayPassesFestival app + its autostart launcher.
COPY daypassesfestival.py /opt/daypassesfestival/daypassesfestival.py
COPY start-daypassesfestival.sh /opt/daypassesfestival/start-daypassesfestival.sh
RUN chmod +x /opt/daypassesfestival/start-daypassesfestival.sh

WORKDIR /app
