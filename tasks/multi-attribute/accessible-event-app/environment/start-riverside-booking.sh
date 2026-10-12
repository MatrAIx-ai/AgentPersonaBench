#!/usr/bin/env bash
set -u
export DISPLAY="${DISPLAY:-:1}"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"
APP=/opt/riverside-booking/riverside_booking.py
APP_PATTERN='^python3 /opt/riverside-booking/riverside_booking.py$'
WINDOW_TITLE='Riverside Booking'
LOG=/tmp/riverside-booking.log

start_app() {
  pgrep -fx "$APP_PATTERN" >/dev/null 2>&1 ||
    setsid nohup python3 "$APP" >>"$LOG" 2>&1 < /dev/null &
}

start_app

keeper() {
  for _ in $(seq 1 3600); do
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
export APP APP_PATTERN WINDOW_TITLE LOG
setsid nohup bash -c "$(declare -f keeper); keeper" >>"$LOG" 2>&1 < /dev/null &

exit 0
