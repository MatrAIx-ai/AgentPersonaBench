# syntax=docker/dockerfile:1.7
# Rowan Till OS-APP desktop: the shared Linux CUA desktop (Xvfb + XFCE + xdotool +
# scrot) PLUS Python Tkinter and the Rowan Till native GUI app baked in. The CUA
# agent (persona-computer-1) drives it by screenshot + coordinate click; when the
# user confirms the order, the app writes /app/output/order.json itself.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# The app + its autostart launcher. The build context is this environment/ dir,
# so the copy baked into the image is environment/app.py — the one that carries
# the per-item ground truth. input/app/app.py is the same catalog with that field
# stripped: it is bind-mounted read-only into the agent's container, nothing reads
# it at runtime, and a byte-identical mounted copy would hand the agent the key.
COPY app.py /opt/app/app.py
COPY start-app.sh /opt/app/start-app.sh
RUN chmod +x /opt/app/start-app.sh

WORKDIR /app
