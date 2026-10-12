# syntax=docker/dockerfile:1.7
#
# HomeBase OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the HomeBase native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms, HomeBase writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The HomeBase app + its autostart launcher.
COPY homebase.py /opt/homebase/homebase.py
COPY start-homebase.sh /opt/homebase/start-homebase.sh
RUN chmod +x /opt/homebase/start-homebase.sh

WORKDIR /app
