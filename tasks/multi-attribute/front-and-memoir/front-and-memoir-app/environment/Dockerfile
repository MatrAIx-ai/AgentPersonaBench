# syntax=docker/dockerfile:1.7
#
# ReelAndPage OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ReelAndPage native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Take pairings", ReelAndPage writes /app/output/pairings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ReelAndPage app + its autostart launcher.
COPY reelandpage.py /opt/reelandpage/reelandpage.py
COPY start-reelandpage.sh /opt/reelandpage/start-reelandpage.sh
RUN chmod +x /opt/reelandpage/start-reelandpage.sh

WORKDIR /app
