# syntax=docker/dockerfile:1.7
#
# BootDeck OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the BootDeck native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Apply setup", BootDeck writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The BootDeck app + its autostart launcher.
COPY bootdeck.py /opt/bootdeck/bootdeck.py
COPY start-bootdeck.sh /opt/bootdeck/start-bootdeck.sh
RUN chmod +x /opt/bootdeck/start-bootdeck.sh

WORKDIR /app
