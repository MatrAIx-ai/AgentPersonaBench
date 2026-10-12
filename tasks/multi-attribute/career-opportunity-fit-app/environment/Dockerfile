# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3-tk fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY careerscout.py /opt/careerscout/careerscout.py
COPY start-careerscout.sh /opt/careerscout/start-careerscout.sh
RUN chmod +x /opt/careerscout/start-careerscout.sh
WORKDIR /app
