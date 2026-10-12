# syntax=docker/dockerfile:1.7
#
# VisitPlan OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the VisitPlan native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve slots", VisitPlan writes /app/output/reservations.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The VisitPlan app + its autostart launcher.
COPY visitplan.py /opt/visitplan/visitplan.py
COPY start-visitplan.sh /opt/visitplan/start-visitplan.sh
RUN chmod +x /opt/visitplan/start-visitplan.sh

WORKDIR /app
