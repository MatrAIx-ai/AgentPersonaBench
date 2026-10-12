# syntax=docker/dockerfile:1.7
# WorkStack OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the WorkStack native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms the setup, WorkStack writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The WorkStack app + its autostart launcher. The build context is this
# environment/ dir, so THIS app.py is the one that runs; it is the only copy that
# carries the per-line org_only ground truth. input/app/app.py is bind-mounted
# read-only into the agent container and is deliberately NOT byte-identical: it
# is the same catalog with the trailing label stripped, because a computer-use
# agent has a terminal and can read anything mounted under /app/input.
COPY app.py /opt/app/app.py
COPY start-app.sh /opt/app/start-app.sh
RUN chmod +x /opt/app/start-app.sh

WORKDIR /app
