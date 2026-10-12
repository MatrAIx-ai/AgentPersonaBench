#!/usr/bin/env bash
set -u
export DISPLAY="${APP_DISPLAY:-:1}"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"
if ! pgrep -f '^python3 /opt/serviceguide/app.py$' >/dev/null 2>&1; then
  setsid nohup python3 /opt/serviceguide/app.py >>/tmp/serviceguide.log 2>&1 < /dev/null &
fi

keeper() {
  for _ in $(seq 1 3600); do
    if ! pgrep -f '^python3 /opt/serviceguide/app.py$' >/dev/null 2>&1; then
      setsid nohup python3 /opt/serviceguide/app.py >>/tmp/serviceguide.log 2>&1 < /dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -qi 'ServiceGuide'; then
      wmctrl -r 'ServiceGuide' -b add,maximized_vert,maximized_horz 2>/dev/null || true
      wmctrl -a 'ServiceGuide' 2>/dev/null || true
    fi
    sleep 0.4
  done
}
setsid nohup bash -c "$(declare -f keeper); keeper" >>/tmp/serviceguide.log 2>&1 < /dev/null &
exit 0
