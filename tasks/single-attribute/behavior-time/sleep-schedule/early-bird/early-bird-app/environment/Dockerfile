# syntax=docker/dockerfile:1.7
#
# TimeChoice native desktop: the shared Linux CUA desktop plus Tkinter. The
# computer-use agent sees screenshots and clicks native controls; the app writes
# the confirmed weekly schedule to /app/output/schedule.json.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/timechoice/app.py
COPY schedule.json /opt/timechoice/schedule.json
COPY start-app.sh /opt/timechoice/start-app.sh
RUN chmod +x /opt/timechoice/start-app.sh

WORKDIR /app
