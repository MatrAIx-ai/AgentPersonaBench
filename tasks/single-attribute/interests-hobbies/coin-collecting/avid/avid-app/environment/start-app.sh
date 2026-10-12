#!/usr/bin/env bash
# Healthcheck bootstraps a singleton keeper; Harbor creates X during agent.setup.
set -u
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/$(basename "${BASH_SOURCE[0]}")"
APP="$SCRIPT_DIR/app.py"
CMD="python3 $APP"
TITLE='Home Hobby Support Desk'
STATE_DIR="${HOBBY_DESK_STATE_DIR:-/tmp/hobby-desk-bootstrap}"
SOCKET_DIR="${HOBBY_DESK_X11_DIR:-/tmp/.X11-unix}"
POLL="${HOBBY_DESK_POLL_SECONDS:-0.25}"
LOG="$STATE_DIR/app.log"
LOCK="$STATE_DIR/keeper.lock"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"

phase() {
  if [ "${LAST_PHASE:-}" != "$1" ]; then
    printf '%s\n' "$1" > "$STATE_DIR/status"
    LAST_PHASE="$1"
  fi
}

pick_display() {
  local socket number
  [ -S "$SOCKET_DIR/X1" ] && { echo ':1'; return 0; }
  for socket in "$SOCKET_DIR"/X*; do
    [ -S "$socket" ] || continue
    number="${socket##*/X}"
    echo ":$number"
    return 0
  done
  return 1
}

keeper() {
  # Lock belongs to this worker, not its app child. A repeated healthcheck
  # creates no duplicate worker; a stopped worker can be bootstrapped again.
  exec 9>"$LOCK"
  flock -n 9 || return 0
  trap 'phase stopped; rm -f "$STATE_DIR/keeper.pid"' EXIT
  trap 'exit 0' TERM INT
  phase waiting-display
  printf '%s\n' "$$" > "$STATE_DIR/keeper.pid"
  local display
  for _ in $(seq 1 14400); do
    if ! display="$(pick_display)"; then
      phase waiting-display
      sleep "$POLL"
      continue
    fi
    export DISPLAY="$display"
    if ! timeout 2 xdpyinfo >/dev/null 2>&1; then
      phase waiting-display
      sleep "$POLL"
      continue
    fi
    if ! timeout 2 wmctrl -m >/dev/null 2>&1; then
      phase waiting-window-manager
      sleep "$POLL"
      continue
    fi
    if ! pgrep -fx "$CMD" >/dev/null 2>&1; then
      phase starting-app
      setsid nohup python3 "$APP" 9>&- >>"$LOG" 2>&1 </dev/null &
      sleep "$POLL"
    fi
    if timeout 2 wmctrl -a "$TITLE" >/dev/null 2>&1; then
      phase window-visible
    fi
    sleep "$POLL"
  done
}

if [ "${1:-}" = --keeper ]; then
  keeper
  exit 0
fi
[ "$#" = 0 ] || { echo "Unexpected launcher argument" >&2; exit 2; }
for dependency in python3 flock pgrep wmctrl xdpyinfo timeout setsid nohup; do
  command -v "$dependency" >/dev/null 2>&1 || {
    echo "Missing bootstrap dependency: $dependency" >&2; exit 1;
  }
done
[ -r "$APP" ] || { echo "Missing native application" >&2; exit 1; }
# Import Tk without constructing a window: valid before an X server exists.
python3 -c 'import ast, pathlib, sys, tkinter; ast.parse(pathlib.Path(sys.argv[1]).read_text())' "$APP" || exit 1
mkdir -p "$STATE_DIR" "$ADHERENCE_OUTPUT_DIR" || exit 1
[ -w "$STATE_DIR" ] && [ -w "$ADHERENCE_OUTPUT_DIR" ] || exit 1
setsid nohup bash "$SCRIPT" --keeper >>"$LOG" 2>&1 </dev/null &
# Acknowledge worker ownership only. Do NOT wait for a display or GUI here:
# run_healthcheck precedes Computer1.setup, which starts Xvfb and XFCE.
for _ in $(seq 1 20); do
  # Never probe/acquire a free lock while the new worker is racing to claim it.
  # A live worker publishes its PID only after acquiring the lock.
  if [ -s "$STATE_DIR/keeper.pid" ]; then
    read -r worker_pid < "$STATE_DIR/keeper.pid"
    if kill -0 "$worker_pid" >/dev/null 2>&1; then
      flock -n "$LOCK" true
      code=$?
      [ "$code" = 1 ] && exit 0
      [ "$code" -le 1 ] || { echo "Cannot inspect keeper lock" >&2; exit 1; }
    fi
  fi
  sleep 0.05
done
echo "Background keeper did not bootstrap" >&2
exit 1
