# syntax=docker/dockerfile:1.7
# Native Linux CUA desktop. Only this task's visible application is added.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk fonts-dejavu-core util-linux \
    && apt-get purge -y xfce4-terminal \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/lend-return/app.py
COPY start-app.sh /opt/lend-return/start-app.sh
COPY chromium-policy.json /etc/chromium/policies/managed/personabench.json
COPY terminal-disabled.desktop /root/.config/xfce4/helpers/custom-TerminalEmulator.desktop

# Preserve screenshot-only operation; there is no user-facing shell workflow.
RUN chmod 0755 /opt/lend-return/start-app.sh \
    && rm -f /usr/share/applications/xfce4-terminal-emulator.desktop \
        /root/.config/xfce4/panel/launcher-17/17884169571.desktop

WORKDIR /app
