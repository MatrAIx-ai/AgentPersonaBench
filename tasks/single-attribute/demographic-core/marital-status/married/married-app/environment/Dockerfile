# syntax=docker/dockerfile:1.7
# Meridian OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Meridian native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms the setup, Meridian writes /app/output/setup.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The Meridian app + its autostart launcher. The build context is this
# environment/ dir, so THIS app.py is the one that runs. Every byte of it ends up
# inside the container and the acting agent has a terminal, so it carries NO
# ground truth: it is the same text as the bind-mounted input/app/app.py, and the
# host-side tests/answer_key.json (never mounted, never copied) is the only place
# the per-line label exists. tests/verifier.py refuses to score a trial if either
# copy of app.py grows a label back.
COPY app.py /opt/app/app.py
COPY start-app.sh /opt/app/start-app.sh
RUN chmod +x /opt/app/start-app.sh

WORKDIR /app
