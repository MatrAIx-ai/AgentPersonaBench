# syntax=docker/dockerfile:1.7
#
# TentTimes OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TentTimes native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book talks", TentTimes writes /app/output/talks.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TentTimes app + its autostart launcher.
COPY tenttimes.py /opt/tenttimes/tenttimes.py
COPY start-tenttimes.sh /opt/tenttimes/start-tenttimes.sh
RUN chmod +x /opt/tenttimes/start-tenttimes.sh

WORKDIR /app
