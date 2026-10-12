#!/usr/bin/env bash
# Launch the QuickSip native GUI on the CUA desktop and KEEP it in front.
#
# The harbor CUA runtime always starts Chromium (about:blank) as the last step of
# desktop bringup, on top. The healthcheck runs before that, so a one-shot raise
# loses to Chromium. Instead we launch QuickSip and spawn a short-lived keeper
# that repeatedly raises QuickSip above it, so by the time the agent takes its
# first screenshot the app — not a browser — fills the screen.
set -u
export DISPLAY="${DISPLAY:-:1}"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

if ! pgrep -f 'python3 /opt/quicksip/quicksip.py$' >/dev/null 2>&1; then
  setsid nohup python3 /opt/quicksip/quicksip.py \
    >>/tmp/quicksip.log 2>&1 < /dev/null &
fi

# Block the healthcheck itself until the window is CONFIRMED up and raised, not
# just launched — a one-shot fire-and-forget here can let the healthcheck report
# "passed" before wmctrl can even see the window, so the agent's first screenshot
# still shows whatever was in front (e.g. Chromium about:blank) instead of the app.
for _ in $(seq 1 50); do  # up to ~15s
  if wmctrl -l 2>/dev/null | grep -qi quicksip; then
    wmctrl -r QuickSip -b add,maximized_vert,maximized_horz 2>/dev/null || true
    wmctrl -a QuickSip 2>/dev/null || true
    break
  fi
  sleep 0.3
done

# Background keeper: the harbor CUA runtime launches Chromium (about:blank) as the
# LAST bringup step (after this healthcheck) and its liveness check REQUIRES a
# running chromium — so we must NOT kill it. Instead keep QuickSip raised above
# it: a full-desktop screenshot then shows the maximized app on top. Runs the
# whole trial so a late Chromium reset() can't keep the app buried.
keeper() {
  for _ in $(seq 1 3600); do
    if ! pgrep -f 'python3 /opt/quicksip/quicksip.py$' >/dev/null 2>&1; then
      setsid nohup python3 /opt/quicksip/quicksip.py >>/tmp/quicksip.log 2>&1 < /dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -qi quicksip; then
      wmctrl -r QuickSip -b add,maximized_vert,maximized_horz 2>/dev/null || true
      wmctrl -a QuickSip 2>/dev/null || true         # raise app above Chromium
    fi
    sleep 0.4
  done
}
setsid nohup bash -c "$(declare -f keeper); keeper" >>/tmp/quicksip.log 2>&1 < /dev/null &

exit 0
