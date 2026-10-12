# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY riverside_booking.py /opt/riverside-booking/riverside_booking.py
COPY start-riverside-booking.sh /opt/riverside-booking/start-riverside-booking.sh
RUN chmod +x /opt/riverside-booking/start-riverside-booking.sh \
    && mkdir -p /root/.config/autostart \
    && printf '%s\n' \
        '[Desktop Entry]' \
        'Type=Application' \
        'Name=Riverside Booking' \
        'Exec=/opt/riverside-booking/start-riverside-booking.sh' \
        'Terminal=false' \
        'X-GNOME-Autostart-enabled=true' \
        > /root/.config/autostart/riverside-booking.desktop

WORKDIR /app
