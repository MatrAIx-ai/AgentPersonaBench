#!/usr/bin/env bash
# Launch the Northstar Experiment Desk GUI and keep it available for the CUA.
#
# persona-computer-1 creates and drives Xvfb on :1, but this healthcheck runs
# before that display exists. Start a detached supervisor now; it waits for :1
# and runs the Tk app in the foreground of its loop, restarting it if it exits.
set -u
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

LOCK=/tmp/.pb_northstar_supervisor
if [ ! -e "$LOCK" ]; then
  : > "$LOCK"
  setsid nohup bash -c '
    export DISPLAY="${APP_DISPLAY:-:1}"
    while true; do
      if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
        python3 /opt/northstar/app.py >>/tmp/northstar.log 2>&1
      fi
      sleep 2
    done
  ' >>/tmp/northstar-supervisor.log 2>&1 < /dev/null &
fi
# Keep the app window above Chromium, which the CUA runtime maps last (after this
# healthcheck). Without this the app is only on top while its own 8-second
# -topmost lasts, and a slow start leaves the agent looking at about:blank.
( export DISPLAY="${DISPLAY:-:1}"
  for _ in $(seq 1 3600); do
    _wid="$(xdotool search --name 'Northstar Experiment Desk' 2>/dev/null | head -1)"
    if [ -n "$_wid" ]; then
      wmctrl -a 'Northstar Experiment Desk' 2>/dev/null || true
      xdotool windowmove "$_wid" 0 0 windowraise "$_wid" 2>/dev/null || true
    fi
    sleep 0.5
  done ) >/dev/null 2>&1 < /dev/null &

exit 0
