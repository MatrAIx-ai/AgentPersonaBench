# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/elm-service/app.py
COPY start-app.sh /opt/elm-service/start-elm-service.sh
RUN chmod +x /opt/elm-service/start-elm-service.sh \
    && mkdir -p /root/.config/autostart \
    && printf '%s\n' \
        '[Desktop Entry]' \
        'Type=Application' \
        'Name=Regional Operations Forum Arrangements' \
        'Exec=/opt/elm-service/start-elm-service.sh' \
        'Terminal=false' \
        'X-GNOME-Autostart-enabled=true' \
        > /root/.config/autostart/elm-service.desktop

WORKDIR /app
