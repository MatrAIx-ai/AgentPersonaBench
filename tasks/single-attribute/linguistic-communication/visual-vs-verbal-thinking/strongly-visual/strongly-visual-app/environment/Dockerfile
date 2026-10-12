# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3-tk fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY app.py /opt/bookdesk/app.py
COPY start-bookdesk.sh /opt/bookdesk/start-bookdesk.sh
RUN chmod +x /opt/bookdesk/start-bookdesk.sh
WORKDIR /app
