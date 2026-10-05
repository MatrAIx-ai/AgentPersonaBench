# syntax=docker/dockerfile:1.7
#
# Errands OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Errands native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, Errands writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Errands app + its autostart launcher.
COPY errands.py /opt/errands/errands.py
COPY start-errands.sh /opt/errands/start-errands.sh
RUN chmod +x /opt/errands/start-errands.sh

WORKDIR /app
