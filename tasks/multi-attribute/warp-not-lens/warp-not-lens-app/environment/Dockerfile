# syntax=docker/dockerfile:1.7
#
# ReelThursday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the ReelThursday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Thursdays", ReelThursday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The ReelThursday app + its autostart launcher.
COPY reelthursday.py /opt/reelthursday/reelthursday.py
COPY start-reelthursday.sh /opt/reelthursday/start-reelthursday.sh
RUN chmod +x /opt/reelthursday/start-reelthursday.sh

WORKDIR /app
