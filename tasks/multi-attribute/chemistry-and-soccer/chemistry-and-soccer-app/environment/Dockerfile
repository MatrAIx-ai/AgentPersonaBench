# syntax=docker/dockerfile:1.7
#
# MatchdayAndLab OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MatchdayAndLab native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", MatchdayAndLab writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MatchdayAndLab app + its autostart launcher.
COPY matchdayandlab.py /opt/matchdayandlab/matchdayandlab.py
COPY start-matchdayandlab.sh /opt/matchdayandlab/start-matchdayandlab.sh
RUN chmod +x /opt/matchdayandlab/start-matchdayandlab.sh

WORKDIR /app
