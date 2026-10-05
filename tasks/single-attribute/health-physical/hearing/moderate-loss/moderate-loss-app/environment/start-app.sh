#!/usr/bin/env bash
set -u
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

LOCK=/tmp/.pb_elm_service_supervisor
if ! mkdir "$LOCK" 2>/dev/null; then
  exit 0
fi

CMD="python3 /opt/elm-service/app.py"
WINDOW_TITLE="Regional Operations Forum Arrangements"
APP_LOG=/tmp/elm-service.log

pick_display() {
  local socket number
  [ -e /tmp/.X11-unix/X1 ] && { echo ":1"; return 0; }
  for socket in /tmp/.X11-unix/X*; do
    [ -e "$socket" ] || continue
    number="${socket##*/X}"
    echo ":$number"
    return 0
  done
  return 1
}

for _ in $(seq 1 60); do
  DISPLAY="$(pick_display)" && { export DISPLAY; break; }
  sleep 0.5
done
export DISPLAY="${DISPLAY:-${APP_DISPLAY:-:1}}"
echo "start-elm-service: using DISPLAY=$DISPLAY" >>"$APP_LOG"

running() { pgrep -fx "$CMD" >/dev/null 2>&1; }
running || setsid nohup $CMD >>"$APP_LOG" 2>&1 </dev/null &

keeper() {
  for _ in $(seq 1 3600); do
    if ! pgrep -fx "$CMD" >/dev/null 2>&1; then
      setsid nohup $CMD >>"$APP_LOG" 2>&1 </dev/null &
      sleep 1
    fi
    wmctrl -a "$WINDOW_TITLE" >/dev/null 2>&1 || true
    sleep 0.4
  done
}
setsid nohup bash -c "export DISPLAY='$DISPLAY' CMD='$CMD' WINDOW_TITLE='$WINDOW_TITLE' APP_LOG='$APP_LOG'; $(declare -f keeper); keeper" \
  >>/tmp/elm-service-supervisor.log 2>&1 </dev/null &

exit 0
