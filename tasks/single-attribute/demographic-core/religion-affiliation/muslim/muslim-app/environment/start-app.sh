#!/usr/bin/env bash
# Launch Juniper Table on Harbor's X11 desktop and keep it above Chromium.
set -u
export DISPLAY=":1"
export ADHERENCE_OUTPUT_DIR="/app/output"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

if ! pgrep -f '^python3 /opt/app/app.py$' >/dev/null 2>&1; then
  setsid nohup python3 /opt/app/app.py >>/tmp/app.log 2>&1 < /dev/null &
fi

keeper() {
  for _ in $(seq 1 3600); do
    if ! pgrep -f '^python3 /opt/app/app.py$' >/dev/null 2>&1; then
      setsid nohup python3 /opt/app/app.py >>/tmp/app.log 2>&1 < /dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -qi "Juniper Table"; then
      wmctrl -r "Juniper Table" -b add,maximized_vert,maximized_horz 2>/dev/null || true
      wmctrl -a "Juniper Table" 2>/dev/null || true
    fi
    sleep 0.4
  done
}

if [ ! -s /tmp/juniper-keeper.pid ] || ! kill -0 "$(cat /tmp/juniper-keeper.pid)" 2>/dev/null; then
  setsid nohup bash -c "$(declare -f keeper); keeper" >>/tmp/app.log 2>&1 < /dev/null &
  echo $! >/tmp/juniper-keeper.pid
fi

exit 0
