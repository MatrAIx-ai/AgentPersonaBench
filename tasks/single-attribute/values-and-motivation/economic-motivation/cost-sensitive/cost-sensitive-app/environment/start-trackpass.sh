#!/usr/bin/env bash
# Launch the TrackPass native GUI on the CUA desktop and KEEP it in front.
#
# Three things bite here, and each one silently ends with the agent screenshotting
# something that is not the app:
#
#  1. DISPLAY. The CUA runtime starts Xvfb AFTER this healthcheck runs, and the
#     shared image sets no DISPLAY. Assuming :0 spawns a GUI that dies instantly on
#     a display that never appears — and the runtime only ever LOOKS at :1. So wait
#     for the socket to exist and prefer :1.
#  2. pgrep -f self-matching. A keeper loop inlined through `bash -c` carries the
#     app's path inside its own command line, so `pgrep -f <path>` always "finds"
#     the app and never respawns it. Match the exact command line with -fx instead.
#  3. Chromium. The runtime launches it (about:blank) as the LAST bringup step,
#     on top, and its liveness check REQUIRES chromium running — so it must not be
#     killed. Keep TrackPass raised above it instead, for the whole trial, so a
#     late reset() cannot bury the app again.
set -u
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

APP=/opt/trackpass/trackpass.py
CMD="python3 $APP"

# --- 1. find the display the runtime actually created -------------------------
# harbor/agents/computer_1/runtime.py pins _DEFAULT_DISPLAY = ":1" and drives every
# xdotool call and screenshot against it, so :1 is the only display the agent can
# actually see. Chromium's own socket can appear as X0 and sorts FIRST in the glob,
# so scanning blindly picks a display the agent never looks at. Prefer :1, and only
# fall back to scanning if the runtime ever stops creating it.
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
echo "start-trackpass: using DISPLAY=$DISPLAY" >>/tmp/trackpass.log

# --- 2 & 3. start it, and keep it alive and raised ----------------------------
running() { pgrep -fx "$CMD" >/dev/null 2>&1; }
running || setsid nohup $CMD >>/tmp/trackpass.log 2>&1 </dev/null &

keeper() {
  for _ in $(seq 1 3600); do
    if ! pgrep -fx "$CMD" >/dev/null 2>&1; then
      setsid nohup $CMD >>/tmp/trackpass.log 2>&1 </dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -qi trackpass; then
      # Raise it, do NOT maximize it. The window is a fixed 1024x866 and
      # resizable(False, False); stretching the frame around it pushes the BOOK
      # button far from the fields and the agent spends its step budget hunting
      # for it instead of using the app.
      wmctrl -a TrackPass 2>/dev/null || true      # raise above chromium
    fi
    sleep 0.4
  done
}
setsid nohup bash -c "export DISPLAY='$DISPLAY' CMD='$CMD'; $(declare -f keeper); keeper" \
  >>/tmp/trackpass.log 2>&1 </dev/null &

exit 0
