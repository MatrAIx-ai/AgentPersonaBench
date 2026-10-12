# syntax=docker/dockerfile:1.7
#
# SettleIn OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SettleIn native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Confirm memberships", SettleIn writes /app/output/memberships.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SettleIn app + its autostart launcher.
COPY settlein.py /opt/settlein/settlein.py
COPY start-settlein.sh /opt/settlein/start-settlein.sh
RUN chmod +x /opt/settlein/start-settlein.sh

WORKDIR /app
