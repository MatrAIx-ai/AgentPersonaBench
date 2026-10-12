# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/flashmart/app.py
COPY start-flashmart.sh /opt/flashmart/start-flashmart.sh
RUN chmod +x /opt/flashmart/start-flashmart.sh \
    && mkdir -p /root/.config/autostart \
    && printf '%s\n' \
        '[Desktop Entry]' \
        'Type=Application' \
        'Name=FlashMart' \
        'Exec=/opt/flashmart/start-flashmart.sh' \
        'Terminal=false' \
        'X-GNOME-Autostart-enabled=true' \
        > /root/.config/autostart/flashmart.desktop

WORKDIR /app
