#!/usr/bin/env bash
# Launch the native app on the CUA desktop (display :1) and keep it raised.
# Runs as the healthcheck: returns 0 immediately and leaves a keeper behind.
set -u
export DISPLAY=":1"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"
APP=/opt/app/app.py
APP_PATTERN='^python3 /opt/app/app.py$'
WINDOW_TITLE='Ridgeline Service Desk'
LOG=/tmp/app.log
KEEPER_LOCK=/tmp/.app-keeper.lock

# One keeper per container: mkdir is atomic, so a second healthcheck call cannot
# race the first into launching a second window on top of the agent's.
mkdir "$KEEPER_LOCK" 2>/dev/null || exit 0

keeper() {
  trap 'rmdir "$KEEPER_LOCK" 2>/dev/null' EXIT
  for _ in $(seq 1 3600); do
    if [ ! -S /tmp/.X11-unix/X1 ]; then
      sleep 0.4
      continue
    fi
    if ! pgrep -fx "$APP_PATTERN" >/dev/null 2>&1; then
      setsid nohup python3 "$APP" >>"$LOG" 2>&1 < /dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -Fqi "$WINDOW_TITLE"; then
      wmctrl -a "$WINDOW_TITLE" >/dev/null 2>&1 || true
    fi
    sleep 0.4
  done
}
export APP APP_PATTERN WINDOW_TITLE LOG KEEPER_LOCK
setsid nohup bash -c "$(declare -f keeper); keeper" >>"$LOG" 2>&1 < /dev/null &
exit 0
