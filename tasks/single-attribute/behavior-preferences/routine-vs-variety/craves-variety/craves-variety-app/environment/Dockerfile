# syntax=docker/dockerfile:1.7
#
# CrateMenu OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CrateMenu native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set my month", CrateMenu writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CrateMenu app + its autostart launcher.
COPY cratemenu.py /opt/cratemenu/cratemenu.py
COPY start-cratemenu.sh /opt/cratemenu/start-cratemenu.sh
RUN chmod +x /opt/cratemenu/start-cratemenu.sh

WORKDIR /app
