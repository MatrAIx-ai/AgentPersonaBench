# syntax=docker/dockerfile:1.7
# PerkPack extends the shared Linux CUA desktop with a native Tkinter app. The
# agent sees screenshots and clicks coordinates; hidden item metadata is never
# drawn on screen.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/perkpack/perkpack.py
COPY start-app.sh /opt/perkpack/start-app.sh
RUN chmod +x /opt/perkpack/start-app.sh

WORKDIR /app
