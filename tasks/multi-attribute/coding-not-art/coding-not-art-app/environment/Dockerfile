# syntax=docker/dockerfile:1.7
#
# TalkLatesMuseum OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TalkLatesMuseum native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book lates", TalkLatesMuseum writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TalkLatesMuseum app + its autostart launcher.
COPY talklatesmuseum.py /opt/talklatesmuseum/talklatesmuseum.py
COPY start-talklatesmuseum.sh /opt/talklatesmuseum/start-talklatesmuseum.sh
RUN chmod +x /opt/talklatesmuseum/start-talklatesmuseum.sh

WORKDIR /app
