# syntax=docker/dockerfile:1.7
#
# MenusThreeWeek OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the MenusThreeWeek native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book plans", MenusThreeWeek writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The MenusThreeWeek app + its autostart launcher.
COPY menusthreeweek.py /opt/menusthreeweek/menusthreeweek.py
COPY start-menusthreeweek.sh /opt/menusthreeweek/start-menusthreeweek.sh
RUN chmod +x /opt/menusthreeweek/start-menusthreeweek.sh

WORKDIR /app
