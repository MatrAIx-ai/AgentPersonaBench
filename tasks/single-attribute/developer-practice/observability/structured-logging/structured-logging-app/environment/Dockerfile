# syntax=docker/dockerfile:1.7
#
# StackKit OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the StackKit native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Save my stack", StackKit writes /app/output/stack.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The StackKit app + its autostart launcher.
COPY stackkit.py /opt/stackkit/stackkit.py
COPY start-stackkit.sh /opt/stackkit/start-stackkit.sh
RUN chmod +x /opt/stackkit/start-stackkit.sh

WORKDIR /app
