# syntax=docker/dockerfile:1.7
#
# ChefCard OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ChefCard native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Place pre-order", ChefCard writes /app/output/preorder.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ChefCard app + its autostart launcher.
COPY chefcard.py /opt/chefcard/chefcard.py
COPY start-chefcard.sh /opt/chefcard/start-chefcard.sh
RUN chmod +x /opt/chefcard/start-chefcard.sh

WORKDIR /app
