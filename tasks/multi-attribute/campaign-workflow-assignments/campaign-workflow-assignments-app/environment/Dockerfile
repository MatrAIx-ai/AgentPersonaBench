FROM matraix/shared-os-app-linux:local
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3-tk fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY choiceapp.py /opt/choiceapp/choiceapp.py
COPY start-app.sh /opt/choiceapp/start-app.sh
RUN chmod +x /opt/choiceapp/start-app.sh
WORKDIR /app
