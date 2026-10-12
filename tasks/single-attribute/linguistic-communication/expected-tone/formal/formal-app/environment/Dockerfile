# syntax=docker/dockerfile:1.7
#
# ReplyDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ReplyDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user sends a reply, ReplyDesk writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ReplyDesk app + its autostart launcher.
COPY replydesk.py /opt/replydesk/replydesk.py
COPY start-replydesk.sh /opt/replydesk/start-replydesk.sh
RUN chmod +x /opt/replydesk/start-replydesk.sh

WORKDIR /app
