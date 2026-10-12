#!/usr/bin/env bash
# Launch CommuteChoice on the X display Harbor actually drives and keep it above
# Chromium without maximizing the fixed-size window.
set -u
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

APP=/opt/commute-benefits/commute_benefits.py
CMD="python3 $APP"
TITLE='CommuteChoice Benefits'
LOG=/tmp/commute-benefits.log

pick_display() {
  local socket number
  [ -e /tmp/.X11-unix/X1 ] && { echo ':1'; return 0; }
  for socket in /tmp/.X11-unix/X*; do
    [ -e "$socket" ] || continue
    number="${socket##*/X}"
    echo ":$number"
    return 0
  done
  return 1
}

for _ in $(seq 1 60); do
  DISPLAY_VALUE="$(pick_display)" && { export DISPLAY="$DISPLAY_VALUE"; break; }
  sleep 0.5
done
export DISPLAY="${DISPLAY:-:1}"

running() { pgrep -fx "$CMD" >/dev/null 2>&1; }
if ! running; then
  setsid nohup $CMD >>"$LOG" 2>&1 </dev/null &
fi

keeper() {
  for _ in $(seq 1 3600); do
    if ! pgrep -fx "$CMD" >/dev/null 2>&1; then
      setsid nohup $CMD >>"$LOG" 2>&1 </dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -Fqi "$TITLE"; then
      wmctrl -a "$TITLE" >/dev/null 2>&1 || true
    fi
    sleep 0.4
  done
}
export CMD TITLE LOG
setsid nohup bash -c "$(declare -f keeper); keeper" >>"$LOG" 2>&1 </dev/null &

exit 0
