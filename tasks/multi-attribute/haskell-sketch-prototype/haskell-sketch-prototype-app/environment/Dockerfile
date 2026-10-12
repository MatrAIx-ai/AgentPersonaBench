# syntax=docker/dockerfile:1.7
#
# PrototypeBench OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the PrototypeBench native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user taps "Reserve prototypes", PrototypeBench writes /app/output/prototype_plan.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The PrototypeBench app + its autostart launcher.
COPY prototypebench.py /opt/prototypebench/prototypebench.py
COPY start-prototypebench.sh /opt/prototypebench/start-prototypebench.sh
RUN chmod +x /opt/prototypebench/start-prototypebench.sh

WORKDIR /app
