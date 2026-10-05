# syntax=docker/dockerfile:1.7
#
# PatioPick OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PatioPick native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Redeem voucher", PatioPick writes /app/output/voucher.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PatioPick app + its autostart launcher.
COPY patiopick.py /opt/patiopick/patiopick.py
COPY start-patiopick.sh /opt/patiopick/start-patiopick.sh
RUN chmod +x /opt/patiopick/start-patiopick.sh

WORKDIR /app
