# syntax=docker/dockerfile:1.7
#
# GearVault OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GearVault native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Spend vouchers", GearVault writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GearVault app + its autostart launcher.
COPY gearvault.py /opt/gearvault/gearvault.py
COPY start-gearvault.sh /opt/gearvault/start-gearvault.sh
RUN chmod +x /opt/gearvault/start-gearvault.sh

WORKDIR /app
