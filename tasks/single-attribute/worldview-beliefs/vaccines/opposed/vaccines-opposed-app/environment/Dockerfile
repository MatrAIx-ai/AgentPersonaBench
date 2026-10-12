# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/northbridge/app.py
COPY start-app.sh /opt/northbridge/start-app.sh
RUN chmod +x /opt/northbridge/start-app.sh
WORKDIR /app
