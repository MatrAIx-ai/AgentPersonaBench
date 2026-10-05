# syntax=docker/dockerfile:1.7
#
# QuickReply OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the QuickReply native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user sends, QuickReply writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The QuickReply app + its autostart launcher.
COPY quickreply.py /opt/quickreply/quickreply.py
COPY start-quickreply.sh /opt/quickreply/start-quickreply.sh
RUN chmod +x /opt/quickreply/start-quickreply.sh

WORKDIR /app
