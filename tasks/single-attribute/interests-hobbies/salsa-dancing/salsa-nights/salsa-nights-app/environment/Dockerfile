# syntax=docker/dockerfile:1.7
#
# CentreClasses OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CentreClasses native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book classes", CentreClasses writes /app/output/classes.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CentreClasses app + its autostart launcher.
COPY centreclasses.py /opt/centreclasses/centreclasses.py
COPY start-centreclasses.sh /opt/centreclasses/start-centreclasses.sh
RUN chmod +x /opt/centreclasses/start-centreclasses.sh

WORKDIR /app
