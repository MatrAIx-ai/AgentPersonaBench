# syntax=docker/dockerfile:1.7
#
# GuildDesk OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the GuildDesk native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Renew year", GuildDesk writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The GuildDesk app + its autostart launcher.
COPY guilddesk.py /opt/guilddesk/guilddesk.py
COPY start-guilddesk.sh /opt/guilddesk/start-guilddesk.sh
RUN chmod +x /opt/guilddesk/start-guilddesk.sh

WORKDIR /app
