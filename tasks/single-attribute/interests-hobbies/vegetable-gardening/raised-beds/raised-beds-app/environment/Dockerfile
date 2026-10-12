# syntax=docker/dockerfile:1.7
#
# PlotStarter OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PlotStarter native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Claim items", PlotStarter writes /app/output/claims.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PlotStarter app + its autostart launcher.
COPY plotstarter.py /opt/plotstarter/plotstarter.py
COPY start-plotstarter.sh /opt/plotstarter/start-plotstarter.sh
RUN chmod +x /opt/plotstarter/start-plotstarter.sh

WORKDIR /app
