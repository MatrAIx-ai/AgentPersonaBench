# syntax=docker/dockerfile:1.7
#
# AwayWeekend OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the AwayWeekend native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book packages", AwayWeekend writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The AwayWeekend app + its autostart launcher.
COPY awayweekend.py /opt/awayweekend/awayweekend.py
COPY start-awayweekend.sh /opt/awayweekend/start-awayweekend.sh
RUN chmod +x /opt/awayweekend/start-awayweekend.sh

WORKDIR /app
