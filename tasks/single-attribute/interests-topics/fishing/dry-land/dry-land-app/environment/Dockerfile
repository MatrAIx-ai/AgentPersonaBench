# syntax=docker/dockerfile:1.7
#
# LakeStay OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the LakeStay native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book activities", LakeStay writes /app/output/activities.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The LakeStay app + its autostart launcher.
COPY lakestay.py /opt/lakestay/lakestay.py
COPY start-lakestay.sh /opt/lakestay/start-lakestay.sh
RUN chmod +x /opt/lakestay/start-lakestay.sh

WORKDIR /app
