# syntax=docker/dockerfile:1.7
#
# Aspire OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Aspire native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Aspire writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Aspire app + its autostart launcher.
COPY aspire.py /opt/aspire/aspire.py
COPY start-aspire.sh /opt/aspire/start-aspire.sh
RUN chmod +x /opt/aspire/start-aspire.sh

WORKDIR /app
