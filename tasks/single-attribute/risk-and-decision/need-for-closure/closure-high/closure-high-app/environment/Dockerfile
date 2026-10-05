# syntax=docker/dockerfile:1.7
#
# SettleUp OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SettleUp native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Make calls", SettleUp writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SettleUp app + its autostart launcher.
COPY settleup.py /opt/settleup/settleup.py
COPY start-settleup.sh /opt/settleup/start-settleup.sh
RUN chmod +x /opt/settleup/start-settleup.sh

WORKDIR /app
