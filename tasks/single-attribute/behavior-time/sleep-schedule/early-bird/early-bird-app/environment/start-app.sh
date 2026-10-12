#!/usr/bin/env bash
# Launch TimeChoice after the computer-use X display is available. The detached
# supervisor keeps the healthcheck non-blocking and restarts the application if
# it exits without relying on a pgrep pattern that can match the supervisor.
set -u
export TIMECHOICE_OUTPUT_DIR="${TIMECHOICE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$TIMECHOICE_OUTPUT_DIR"

LOCK=/tmp/.pb_timechoice_supervisor
if [ ! -e "$LOCK" ]; then
  : > "$LOCK"
  setsid nohup bash -c '
    export DISPLAY="${APP_DISPLAY:-:1}"
    while true; do
      # Tk needs the window manager to honor its initial stacking hint.
      if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1 && wmctrl -m >/dev/null 2>&1; then
        python3 /opt/timechoice/app.py >>/tmp/timechoice.log 2>&1
      fi
      sleep 2
    done
  ' >>/tmp/timechoice-supervisor.log 2>&1 < /dev/null &
fi
# Keep the app window above Chromium, which the CUA runtime maps last (after this
# healthcheck). Without this the app is only on top while its own 8-second
# -topmost lasts, and a slow start leaves the agent looking at about:blank.
( export DISPLAY="${DISPLAY:-:1}"
  for _ in $(seq 1 3600); do
    _wid="$(xdotool search --name 'TimeChoice' 2>/dev/null | head -1)"
    if [ -n "$_wid" ]; then
      wmctrl -a 'TimeChoice' 2>/dev/null || true
      xdotool windowmove "$_wid" 0 0 windowraise "$_wid" 2>/dev/null || true
    fi
    sleep 0.5
  done ) >/dev/null 2>&1 < /dev/null &

exit 0
