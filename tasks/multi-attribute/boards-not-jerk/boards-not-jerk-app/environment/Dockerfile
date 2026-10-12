# syntax=docker/dockerfile:1.7
#
# DayBundlesLake OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the DayBundlesLake native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Book days", DayBundlesLake writes /app/output/bookings.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The DayBundlesLake app + its autostart launcher.
COPY daybundleslake.py /opt/daybundleslake/daybundleslake.py
COPY start-daybundleslake.sh /opt/daybundleslake/start-daybundleslake.sh
RUN chmod +x /opt/daybundleslake/start-daybundleslake.sh

WORKDIR /app
