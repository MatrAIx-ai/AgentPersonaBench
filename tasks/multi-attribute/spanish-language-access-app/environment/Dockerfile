# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/serviceguide/app.py
COPY start-app.sh /opt/serviceguide/start-serviceguide.sh
RUN chmod +x /opt/serviceguide/start-serviceguide.sh

WORKDIR /app
