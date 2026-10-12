# syntax=docker/dockerfile:1.7
#
# TalkAndFightNight OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TalkAndFightNight native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", TalkAndFightNight writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TalkAndFightNight app + its autostart launcher.
COPY talkandfightnight.py /opt/talkandfightnight/talkandfightnight.py
COPY start-talkandfightnight.sh /opt/talkandfightnight/start-talkandfightnight.sh
RUN chmod +x /opt/talkandfightnight/start-talkandfightnight.sh

WORKDIR /app
