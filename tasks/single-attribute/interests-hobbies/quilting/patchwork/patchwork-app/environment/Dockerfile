# syntax=docker/dockerfile:1.7
#
# CraftVoucher OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CraftVoucher native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Redeem voucher", CraftVoucher writes /app/output/voucher.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CraftVoucher app + its autostart launcher.
COPY craftvoucher.py /opt/craftvoucher/craftvoucher.py
COPY start-craftvoucher.sh /opt/craftvoucher/start-craftvoucher.sh
RUN chmod +x /opt/craftvoucher/start-craftvoucher.sh

WORKDIR /app
