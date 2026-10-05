#!/usr/bin/env bash
set -u
# Resolve the live X display: harbor's CUA runtime serves the desktop on :1
# (not :0), so ask the X socket dir rather than assuming, and fall back to
# :1 for the cold-start case where the healthcheck runs before Xvfb is up —
# the keeper below relaunches the app until the display exists.
if [ -z "${DISPLAY:-}" ]; then
  for _xs in /tmp/.X11-unix/X*; do
    [ -e "$_xs" ] && DISPLAY=":${_xs##*X}"
  done
fi
export DISPLAY="${DISPLAY:-:1}"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"
APP_PATTERN='^python3 /opt/shelter-register/shelter_register.py'
WINDOW_TITLE='SafeHarbor Registration'
LOG=/tmp/shelter-register.log

start_app() {
  pgrep -f "$APP_PATTERN" >/dev/null 2>&1 ||
    setsid nohup python3 /opt/shelter-register/shelter_register.py >>"$LOG" 2>&1 </dev/null &
}

start_app

keeper() {
  for _ in $(seq 1 3600); do
    if ! pgrep -f "$APP_PATTERN" >/dev/null 2>&1; then
      setsid nohup python3 /opt/shelter-register/shelter_register.py >>"$LOG" 2>&1 </dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -Fqi "$WINDOW_TITLE"; then
      wmctrl -r "$WINDOW_TITLE" -b add,maximized_vert,maximized_horz >/dev/null 2>&1 || true
      wmctrl -a "$WINDOW_TITLE" >/dev/null 2>&1 || true
    fi
    sleep 0.4
  done
}
export APP_PATTERN WINDOW_TITLE LOG
setsid nohup bash -c "$(declare -f keeper); keeper" >>"$LOG" 2>&1 </dev/null &

exit 0
