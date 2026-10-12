# syntax=docker/dockerfile:1.7
# TripBuilder OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the TripBuilder native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms the plan, TripBuilder writes /app/output/plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The TripBuilder app + its autostart launcher. The build context is this
# environment/ dir; app.py here stays byte-identical to input/app/app.py.
COPY app.py /opt/app/app.py
COPY start-app.sh /opt/app/start-app.sh
RUN chmod +x /opt/app/start-app.sh

WORKDIR /app
