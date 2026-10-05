#!/usr/bin/env bash
# Launch CulturePass and keep its native window above Chromium during the trial.
set -u
# Resolve the live X display: harbor's CUA runtime serves the desktop on :1
# (not :0), so ask the X socket dir rather than assuming, and fall back to
# :1 for the cold-start case where the healthcheck runs before Xvfb is up —
# the keeper below relaunches the app until the display exists.
if [ -z "${DISPLAY:-}" ]; then
  for _xs in /tmp/.X11-unix/X*; do
    [ -e "$_xs" ] && DISPLAY=":${_xs##*X}"
  done
fi
export DISPLAY="${DISPLAY:-:1}"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

if ! pgrep -f /opt/culturepass/culturepass.py >/dev/null 2>&1; then
  setsid nohup python3 /opt/culturepass/culturepass.py >>/tmp/culturepass.log 2>&1 < /dev/null &
fi

keeper() {
  # Assemble the app path at runtime: this function's SOURCE rides inside
  # the keeper shell's own command line, so a contiguous literal path here
  # would make the liveness pgrep match the keeper itself and mask every
  # crash — the bug that kept dead apps dead in every recorded trial.
  local app=/opt/culturepass/culturepass
  app="$app.py"
  for _ in $(seq 1 3600); do
    if ! pgrep -f "$app" >/dev/null 2>&1; then
      setsid nohup python3 "$app" >>/tmp/culturepass.log 2>&1 < /dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -qi culturepass; then
      wmctrl -r CulturePass -b add,maximized_vert,maximized_horz 2>/dev/null || true
      wmctrl -a CulturePass 2>/dev/null || true
    fi
    sleep 0.4
  done
}
setsid nohup bash -c "$(declare -f keeper); keeper" >>/tmp/culturepass.log 2>&1 < /dev/null &

exit 0
