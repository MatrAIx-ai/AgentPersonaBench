# syntax=docker/dockerfile:1.7
#
# SafePlan OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the SafePlan native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, SafePlan writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The SafePlan app + its autostart launcher.
COPY safeplan.py /opt/safeplan/safeplan.py
COPY start-safeplan.sh /opt/safeplan/start-safeplan.sh
RUN chmod +x /opt/safeplan/start-safeplan.sh

WORKDIR /app
