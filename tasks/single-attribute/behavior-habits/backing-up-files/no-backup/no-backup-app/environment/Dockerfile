# syntax=docker/dockerfile:1.7
#
# FirstBoot OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the FirstBoot native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Confirm extras", FirstBoot writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The FirstBoot app + its autostart launcher.
COPY firstboot.py /opt/firstboot/firstboot.py
COPY start-firstboot.sh /opt/firstboot/start-firstboot.sh
RUN chmod +x /opt/firstboot/start-firstboot.sh

WORKDIR /app
