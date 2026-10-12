# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY washermart.py /opt/washermart/washermart.py
COPY start-washermart.sh /opt/washermart/start-washermart.sh
RUN chmod +x /opt/washermart/start-washermart.sh \
    && mkdir -p /root/.config/autostart \
    && printf '%s\n' \
        '[Desktop Entry]' \
        'Type=Application' \
        'Name=WasherMart' \
        'Exec=/opt/washermart/start-washermart.sh' \
        'Terminal=false' \
        'X-GNOME-Autostart-enabled=true' \
        > /root/.config/autostart/washermart.desktop

WORKDIR /app
