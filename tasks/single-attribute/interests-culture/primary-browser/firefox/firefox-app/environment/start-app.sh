#!/usr/bin/env bash
set -u
export DISPLAY=":1"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

keeper() {
  for _ in $(seq 1 3600); do
    if [ ! -S /tmp/.X11-unix/X1 ]; then
      sleep 0.4
      continue
    fi
    if ! pgrep -f '^python3 /opt/app/app.py$' >/dev/null 2>&1; then
      setsid nohup python3 /opt/app/app.py >>/tmp/research-desk.log 2>&1 < /dev/null &
      sleep 1
    fi
    if [ ! -f /tmp/research-browser-selected ] && wmctrl -l 2>/dev/null | grep -Fqi "Research Desk"; then
      wmctrl -r "Research Desk" -b add,maximized_vert,maximized_horz 2>/dev/null || true
      wmctrl -a "Research Desk" 2>/dev/null || true
    fi
    sleep 0.4
  done
}
setsid nohup bash -c "$(declare -f keeper); keeper" >>/tmp/research-desk.log 2>&1 < /dev/null &
exit 0
