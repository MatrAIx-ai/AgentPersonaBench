#!/usr/bin/env bash
# Launch the FlashMart native GUI on the CUA desktop and KEEP it in front.
#
# Bringup order on the docker_computer1 backend: this healthcheck runs FIRST,
# then the computer-1 runtime starts Xvfb on :1 + XFCE + Chromium (about:blank,
# raised last, and its liveness check requires Chromium — never kill it). So the
# healthcheck cannot draw anything yet: no X display exists, and the image sets
# no DISPLAY env. Everything display-dependent therefore lives in a background
# keeper that (a) waits for whatever X socket the runtime creates and resolves
# DISPLAY from it — never hardcode :0 — then (b) keeps FlashMart alive and
# raised above Chromium for the whole trial, so every agent screenshot shows the
# maximized app rather than the blank browser.
set -u
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"
APP=/opt/flashmart/app.py
APP_PATTERN='^python3 /opt/flashmart/app.py'
WINDOW_TITLE=FlashMart
LOG=/tmp/flashmart.log
export APP APP_PATTERN WINDOW_TITLE LOG

keeper() {
  # Phase 1: wait (up to ~5 min) for the CUA runtime's X display.
  for _ in $(seq 1 300); do
    sock=$(ls /tmp/.X11-unix/X* 2>/dev/null | head -1)
    [ -n "${sock:-}" ] && break
    sleep 1
  done
  [ -n "${sock:-}" ] || exit 0
  export DISPLAY=":${sock##*/X}"

  # Phase 2: keep the app running and on top.
  for _ in $(seq 1 3600); do
    if ! pgrep -f "$APP_PATTERN" >/dev/null 2>&1; then
      setsid nohup python3 "$APP" >>"$LOG" 2>&1 < /dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -Fqi "$WINDOW_TITLE"; then
      wmctrl -r "$WINDOW_TITLE" -b add,maximized_vert,maximized_horz >/dev/null 2>&1 || true
      wmctrl -a "$WINDOW_TITLE" >/dev/null 2>&1 || true
    fi
    sleep 0.4
  done
}
setsid nohup bash -c "$(declare -f keeper); keeper" >>"$LOG" 2>&1 < /dev/null &

exit 0
