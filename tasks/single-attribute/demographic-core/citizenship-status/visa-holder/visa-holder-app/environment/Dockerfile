# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/pathway/app.py
COPY start-app.sh /opt/pathway/start-pathway.sh
RUN chmod +x /opt/pathway/start-pathway.sh

WORKDIR /app
