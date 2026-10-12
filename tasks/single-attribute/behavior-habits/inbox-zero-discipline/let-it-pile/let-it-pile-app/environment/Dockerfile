# syntax=docker/dockerfile:1.7
#
# InboxSetup OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the InboxSetup native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Save preferences", InboxSetup writes /app/output/preferences.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The InboxSetup app + its autostart launcher.
COPY inboxsetup.py /opt/inboxsetup/inboxsetup.py
COPY start-inboxsetup.sh /opt/inboxsetup/start-inboxsetup.sh
RUN chmod +x /opt/inboxsetup/start-inboxsetup.sh

WORKDIR /app
