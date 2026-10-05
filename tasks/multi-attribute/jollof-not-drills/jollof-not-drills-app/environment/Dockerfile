# syntax=docker/dockerfile:1.7
#
# PlansSaturday OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PlansSaturday native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book Saturdays", PlansSaturday writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PlansSaturday app + its autostart launcher.
COPY planssaturday.py /opt/planssaturday/planssaturday.py
COPY start-planssaturday.sh /opt/planssaturday/start-planssaturday.sh
RUN chmod +x /opt/planssaturday/start-planssaturday.sh

WORKDIR /app
