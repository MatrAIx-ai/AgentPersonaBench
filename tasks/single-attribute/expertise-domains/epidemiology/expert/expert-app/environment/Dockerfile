# syntax=docker/dockerfile:1.7
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY causal_study_audit.py /opt/causal-audit/causal_study_audit.py
COPY start-causal-audit.sh /opt/causal-audit/start-causal-audit.sh
RUN chmod +x /opt/causal-audit/start-causal-audit.sh \
    && mkdir -p /root/.config/autostart \
    && printf '%s\n' \
        '[Desktop Entry]' \
        'Type=Application' \
        'Name=Causal Study Audit' \
        'Exec=/opt/causal-audit/start-causal-audit.sh' \
        'Terminal=false' \
        'X-GNOME-Autostart-enabled=true' \
        > /root/.config/autostart/causal-audit.desktop

WORKDIR /app

