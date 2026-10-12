# syntax=docker/dockerfile:1.7
#
# TermDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TermDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Set terms", TermDesk writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TermDesk app + its autostart launcher.
COPY termdesk.py /opt/termdesk/termdesk.py
COPY start-termdesk.sh /opt/termdesk/start-termdesk.sh
RUN chmod +x /opt/termdesk/start-termdesk.sh

WORKDIR /app
