# syntax=docker/dockerfile:1.7
# MeetLocal native Linux CUA desktop. The app writes its confirmed shortlist to
# /app/output/selection.json after real screenshot-and-coordinate interaction.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/app/app.py
COPY start-app.sh /opt/app/start-app.sh
RUN chmod +x /opt/app/start-app.sh

WORKDIR /app
