# syntax=docker/dockerfile:1.7
#
# CaseCloset OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the CaseCloset native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Pack these", CaseCloset writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The CaseCloset app + its autostart launcher.
COPY casecloset.py /opt/casecloset/casecloset.py
COPY start-casecloset.sh /opt/casecloset/start-casecloset.sh
RUN chmod +x /opt/casecloset/start-casecloset.sh

WORKDIR /app
