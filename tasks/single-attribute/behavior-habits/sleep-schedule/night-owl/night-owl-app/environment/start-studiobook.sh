#!/usr/bin/env bash
# Launch the StudioBook GUI and keep it available for the CUA.
#
# Two constraints shape this:
#   1. The display is :1, not :0. persona-computer-1 runs `Xvfb :1` and drives
#      every xdotool call and screenshot against :1 (harbor/agents/computer_1/
#      runtime.py, _DEFAULT_DISPLAY). A GUI started on :0 is invisible to the
#      agent, which then sees only Chromium's about:blank and spends its whole
#      step budget hunting for a URL that does not exist.
#   2. This healthcheck runs during environment bringup, BEFORE the agent starts
#      Xvfb, so the GUI cannot be launched synchronously here.
#
# Hence a detached supervisor that waits for :1 and then runs the app in the
# foreground of its loop, restarting it if it ever exits. Deliberately no
# `pgrep -f python3 /opt/studiobook/studiobook.py` guard: the supervisor's own command line
# contains that string, so pgrep matches itself and the app is never started.
set -u
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

LOCK=/tmp/.pb_studiobook_supervisor
if [ ! -e "$LOCK" ]; then
  : > "$LOCK"
  setsid nohup bash -c '
    export DISPLAY="${APP_DISPLAY:-:1}"
    while true; do
      if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
        python3 /opt/studiobook/studiobook.py >>/tmp/studiobook.log 2>&1
      fi
      sleep 2
    done
  ' >>/tmp/studiobook-supervisor.log 2>&1 < /dev/null &
fi
# Keep the app window above Chromium, which the CUA runtime maps last (after this
# healthcheck). Without this the app is only on top while its own 8-second
# -topmost lasts, and a slow start leaves the agent looking at about:blank.
( export DISPLAY="${DISPLAY:-:1}"
  for _ in $(seq 1 3600); do
    _wid="$(xdotool search --name 'StudioBook' 2>/dev/null | head -1)"
    if [ -n "$_wid" ]; then
      wmctrl -a 'StudioBook' 2>/dev/null || true
      xdotool windowmove "$_wid" 0 0 windowraise "$_wid" 2>/dev/null || true
    fi
    sleep 0.5
  done ) >/dev/null 2>&1 < /dev/null &

exit 0
