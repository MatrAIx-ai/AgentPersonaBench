# syntax=docker/dockerfile:1.7
#
# NoonBox OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the NoonBox native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Order lunches", NoonBox writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The NoonBox app + its autostart launcher.
COPY noonbox.py /opt/noonbox/noonbox.py
COPY start-noonbox.sh /opt/noonbox/start-noonbox.sh
RUN chmod +x /opt/noonbox/start-noonbox.sh

WORKDIR /app
