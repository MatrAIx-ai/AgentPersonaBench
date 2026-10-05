# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends python3-tk fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY shelter_register.py /opt/shelter-register/shelter_register.py
COPY start-shelter-register.sh /opt/shelter-register/start-shelter-register.sh
RUN chmod +x /opt/shelter-register/start-shelter-register.sh \
    && mkdir -p /root/.config/autostart \
    && printf '%s\n' \
        '[Desktop Entry]' \
        'Type=Application' \
        'Name=SafeHarbor Registration' \
        'Exec=/opt/shelter-register/start-shelter-register.sh' \
        'Terminal=false' \
        'X-GNOME-Autostart-enabled=true' \
        > /root/.config/autostart/shelter-register.desktop
WORKDIR /app
