#!/usr/bin/env bash
# Launch the Kestrel Itinerary Builder GUI and keep it available for the CUA agent.
#
# Two constraints shape this:
#   1. The desktop is served on :1, not :0. persona-computer-1 runs `Xvfb :1`
#      and prefixes every xdotool call and screenshot with DISPLAY=:1
#      (harbor/agents/computer_1/runtime.py, _DEFAULT_DISPLAY), but never
#      exports it, so this script resolves the live socket instead of assuming.
#   2. This healthcheck runs during environment bringup, BEFORE the agent's
#      Xvfb is up, so the GUI cannot be launched synchronously here.
#
# Hence a detached supervisor that waits for the display and then runs the app
# from its loop, restarting it if it ever exits, and raising its window. The app path is
# assembled at runtime so the supervisor's own command line does not contain it:
# a `pgrep -f` for a contiguous literal would match the supervisor itself and a
# dead app would never be respawned — this supervisor uses no pgrep at all.
set -u
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

LOCK=/tmp/.pb_kestrel_supervisor
if [ ! -e "$LOCK" ]; then
  : > "$LOCK"
  setsid nohup bash -c '
    if [ -z "${DISPLAY:-}" ]; then
      for _xs in /tmp/.X11-unix/X*; do
        [ -e "$_xs" ] && DISPLAY=":${_xs##*X}"
      done
    fi
    export DISPLAY="${DISPLAY:-:1}"
    APP="/opt/kestrel/""kestrel.py"
    while true; do
      if xdpyinfo -display "$DISPLAY" >/dev/null 2>&1; then
        python3 "$APP" >>/tmp/kestrel.log 2>&1 &
        APP_PID=$!
        # The CUA runtime starts (and on reset() restarts) a maximized Chromium
        # AFTER this healthcheck, which would bury the kiosk. Keep raising the
        # window by its title for as long as the app process is alive.
        while kill -0 "$APP_PID" 2>/dev/null; do
          wmctrl -a "Kestrel Itinerary Builder" >/dev/null 2>&1 || true
          sleep 2
        done
      fi
      sleep 2
    done
  ' >>/tmp/kestrel-supervisor.log 2>&1 < /dev/null &
fi
exit 0
