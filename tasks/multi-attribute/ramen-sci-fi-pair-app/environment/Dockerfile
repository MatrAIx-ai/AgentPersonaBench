# syntax=docker/dockerfile:1.7
# Set Menu OS-APP desktop: shared Linux CUA desktop plus the native Tkinter
# queue application. The app writes /app/output/order_result.json.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# app.py stays byte-identical to the canonical input/app/app.py.
COPY app.py /opt/app/app.py
COPY start-app.sh /opt/app/start-app.sh
RUN chmod +x /opt/app/start-app.sh

WORKDIR /app
