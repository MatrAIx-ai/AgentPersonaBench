#!/usr/bin/env bash
set -u
export DISPLAY="${DISPLAY:-:1}"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"
if ! pgrep -f '^python3 /opt/app/app.py$' >/dev/null 2>&1; then
  setsid nohup python3 /opt/app/app.py >>/tmp/patch-desk.log 2>&1 < /dev/null &
fi
# Chromium is started after the healthcheck, so keep the native app raised for
# the entire CUA trial rather than losing it behind the browser window.
keeper() {
  for _ in $(seq 1 3600); do
    if ! pgrep -f '^python3 /opt/app/app.py$' >/dev/null 2>&1; then
      setsid nohup python3 /opt/app/app.py >>/tmp/patch-desk.log 2>&1 < /dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -qi 'Patch Desk'; then
      wmctrl -r 'Patch Desk' -b add,maximized_vert,maximized_horz 2>/dev/null || true
      wmctrl -a 'Patch Desk' 2>/dev/null || true
    fi
    sleep 0.4
  done
}
setsid nohup bash -c "$(declare -f keeper); keeper" >>/tmp/patch-desk.log 2>&1 < /dev/null &
exit 0
