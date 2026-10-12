# syntax=docker/dockerfile:1.7
# CulturePass extends the shared Linux CUA desktop with a native Tkinter app.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/culturepass/culturepass.py
COPY start-app.sh /opt/culturepass/start-app.sh
RUN chmod +x /opt/culturepass/start-app.sh

WORKDIR /app
