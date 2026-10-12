# syntax=docker/dockerfile:1.7
#
# GateCredit OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GateCredit native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book access", GateCredit writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GateCredit app + its autostart launcher.
COPY gatecredit.py /opt/gatecredit/gatecredit.py
COPY start-gatecredit.sh /opt/gatecredit/start-gatecredit.sh
RUN chmod +x /opt/gatecredit/start-gatecredit.sh

WORKDIR /app
