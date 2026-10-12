# syntax=docker/dockerfile:1.7
#
# KitVoucher OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the KitVoucher native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Redeem voucher", KitVoucher writes /app/output/voucher.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The KitVoucher app + its autostart launcher.
COPY kitvoucher.py /opt/kitvoucher/kitvoucher.py
COPY start-kitvoucher.sh /opt/kitvoucher/start-kitvoucher.sh
RUN chmod +x /opt/kitvoucher/start-kitvoucher.sh

WORKDIR /app
