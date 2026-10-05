# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/statdesk/app.py
COPY start-app.sh /opt/statdesk/start-statdesk.sh
RUN chmod +x /opt/statdesk/start-statdesk.sh \
    && mkdir -p /root/.config/autostart \
    && printf '%s\n' \
        '[Desktop Entry]' \
        'Type=Application' \
        'Name=Meridian Review Desk' \
        'Exec=/opt/statdesk/start-statdesk.sh' \
        'Terminal=false' \
        'X-GNOME-Autostart-enabled=true' \
        > /root/.config/autostart/statdesk.desktop

WORKDIR /app
