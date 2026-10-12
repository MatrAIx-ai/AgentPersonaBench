# syntax=docker/dockerfile:1.7
#
# SplitSlip OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SplitSlip native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Apply rules", SplitSlip writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SplitSlip app + its autostart launcher.
COPY splitslip.py /opt/splitslip/splitslip.py
COPY start-splitslip.sh /opt/splitslip/start-splitslip.sh
RUN chmod +x /opt/splitslip/start-splitslip.sh

WORKDIR /app
