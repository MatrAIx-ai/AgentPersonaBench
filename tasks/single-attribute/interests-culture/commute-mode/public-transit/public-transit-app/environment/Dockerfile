# syntax=docker/dockerfile:1.7
# CommuteChoice: task-local Linux CUA desktop with the native Tkinter app.
FROM matraix/shared-os-app-linux:local

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-tk \
        fonts-dejavu-core \
    && apt-get purge -y xfce4-terminal \
    && rm -rf /var/lib/apt/lists/*

COPY app.py /opt/commute-benefits/commute_benefits.py
COPY start-app.sh /opt/commute-benefits/start-commute-benefits.sh
COPY chromium-policy.json /etc/chromium/policies/managed/personabench.json
COPY terminal-disabled.desktop /root/.config/xfce4/helpers/custom-TerminalEmulator.desktop

# This native-GUI task never needs a user-facing shell. Disable the terminal
# inherited from the shared desktop and block Chromium from opening local files,
# so the screenshot-only agent remains confined to the visible interface and
# the app-written submission flow.
RUN chmod +x /opt/commute-benefits/start-commute-benefits.sh \
    && rm -f /usr/share/applications/xfce4-terminal-emulator.desktop \
        /root/.config/xfce4/panel/launcher-17/17884169571.desktop

WORKDIR /app
