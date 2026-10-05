# syntax=docker/dockerfile:1.7
#
# Composer OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Composer native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Composer writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Composer app + its autostart launcher.
COPY composer.py /opt/composer/composer.py
COPY start-composer.sh /opt/composer/start-composer.sh
RUN chmod +x /opt/composer/start-composer.sh

WORKDIR /app
