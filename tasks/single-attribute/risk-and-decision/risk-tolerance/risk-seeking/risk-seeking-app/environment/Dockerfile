# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/biddesk/app.py
COPY workflows.json /opt/biddesk/workflows.json
COPY start-app.sh /opt/biddesk/start-biddesk.sh
RUN chmod +x /opt/biddesk/start-biddesk.sh \
    && mkdir -p /root/.config/autostart \
    && printf '%s\n' \
        '[Desktop Entry]' \
        'Type=Application' \
        'Name=BidDesk Opportunity Workspace' \
        'Exec=/opt/biddesk/start-biddesk.sh' \
        'Terminal=false' \
        'X-GNOME-Autostart-enabled=true' \
        > /root/.config/autostart/biddesk.desktop

WORKDIR /app
