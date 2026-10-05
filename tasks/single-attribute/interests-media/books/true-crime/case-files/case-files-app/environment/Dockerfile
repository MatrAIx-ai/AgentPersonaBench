# syntax=docker/dockerfile:1.7
#
# TablePick OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TablePick native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Take these three", TablePick writes /app/output/titles.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TablePick app + its autostart launcher.
COPY tablepick.py /opt/tablepick/tablepick.py
COPY start-tablepick.sh /opt/tablepick/start-tablepick.sh
RUN chmod +x /opt/tablepick/start-tablepick.sh

WORKDIR /app
