#!/usr/bin/env bash
# Launch the CartPop native GUI on the CUA desktop and KEEP it in front.
#
# Three things bite here, and each one ends with the agent screenshotting
# something that is not the app:
#
#  1. DISPLAY. The CUA runtime starts Xvfb AFTER this healthcheck runs, and the
#     shared image sets no DISPLAY. Assuming :0 spawns a GUI that dies instantly
#     on a display that never appears. Worse, the runtime only ever LOOKS at :1:
#     harbor/agents/computer_1/runtime.py pins _DEFAULT_DISPLAY = ":1" and drives
#     every xdotool call and screenshot against it, while a stray X0 socket sorts
#     FIRST in the glob. So wait for a socket and prefer :1.
#  2. pgrep -f self-matching. A keeper loop inlined through `bash -c` carries the
#     app's path inside its own command line, so `pgrep -f <path>` always "finds"
#     the app and never respawns it. Match the exact command line with -fx.
#  3. Chromium. The runtime launches it (about:blank) as the LAST bringup step, on
#     top, and its liveness check REQUIRES chromium running, so it must not be
#     killed. Keep CartPop raised above it instead, for the whole trial, so a late
#     reset() cannot bury the app again.
#
# CartPop maximizes itself (`-zoomed`), so the keeper only raises: re-maximizing
# from outside would fight the app for its own geometry.
set -u
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

APP=/opt/cartpop/cartpop.py
CMD="python3 $APP"

# --- 1. find the display the runtime actually drives --------------------------
pick_display() {
  local s n
  [ -e /tmp/.X11-unix/X1 ] && { echo ":1"; return 0; }
  for s in /tmp/.X11-unix/X*; do
    [ -e "$s" ] || continue
    n="${s##*/X}"
    echo ":$n"
    return 0
  done
  return 1
}
for _ in $(seq 1 60); do
  D="$(pick_display)" && { export DISPLAY="$D"; break; }
  sleep 0.5
done
export DISPLAY="${DISPLAY:-:1}"
echo "start-cartpop: using DISPLAY=$DISPLAY" >>/tmp/cartpop.log

# --- 2 & 3. start it, and keep it alive and raised ----------------------------
# The keeper runs for the whole trial and respawns the app whenever it exits,
# which also covers the case where this healthcheck gave up waiting and the X
# server only appeared later.
pgrep -fx "$CMD" >/dev/null 2>&1 || setsid nohup $CMD >>/tmp/cartpop.log 2>&1 </dev/null &

keeper() {
  for _ in $(seq 1 3600); do
    if ! pgrep -fx "$CMD" >/dev/null 2>&1; then
      setsid nohup $CMD >>/tmp/cartpop.log 2>&1 </dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -qi cartpop; then
      wmctrl -a CartPop 2>/dev/null || true    # raise above chromium, never resize
    fi
    sleep 0.4
  done
}
setsid nohup bash -c "export DISPLAY='$DISPLAY' CMD='$CMD'; $(declare -f keeper); keeper" \
  >>/tmp/cartpop.log 2>&1 </dev/null &

exit 0
