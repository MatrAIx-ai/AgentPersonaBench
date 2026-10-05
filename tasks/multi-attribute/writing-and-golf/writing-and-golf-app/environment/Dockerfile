# syntax=docker/dockerfile:1.7
#
# MatchdayAndClass OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MatchdayAndClass native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", MatchdayAndClass writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MatchdayAndClass app + its autostart launcher.
COPY matchdayandclass.py /opt/matchdayandclass/matchdayandclass.py
COPY start-matchdayandclass.sh /opt/matchdayandclass/start-matchdayandclass.sh
RUN chmod +x /opt/matchdayandclass/start-matchdayandclass.sh

WORKDIR /app
