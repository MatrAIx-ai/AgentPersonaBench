# syntax=docker/dockerfile:1.7
#
# ViewSetup OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ViewSetup native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps Apply, ViewSetup writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ViewSetup app + its autostart launcher.
COPY viewsetup.py /opt/viewsetup/viewsetup.py
COPY start-viewsetup.sh /opt/viewsetup/start-viewsetup.sh
RUN chmod +x /opt/viewsetup/start-viewsetup.sh

WORKDIR /app
