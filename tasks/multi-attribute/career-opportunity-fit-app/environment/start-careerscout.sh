#!/usr/bin/env bash
# The healthcheck runs before computer-1 creates its X server. Start a keeper in
# the background; it waits for the display the agent actually screenshots, then
# keeps the native app alive and raised above Chromium for the whole trial.
set -u
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

keeper() {
  local sock=""
  for _ in $(seq 1 300); do
    if [ -e /tmp/.X11-unix/X1 ]; then
      sock=/tmp/.X11-unix/X1
      break
    fi
    sock=$(ls /tmp/.X11-unix/X* 2>/dev/null | head -1)
    [ -n "${sock:-}" ] && break
    sleep 1
  done
  [ -n "${sock:-}" ] || exit 0
  export DISPLAY=":${sock##*/X}"
  echo "start-careerscout: using DISPLAY=$DISPLAY" >>/tmp/careerscout.log
  for _ in $(seq 1 3600); do
    if ! pgrep -fx "python3 /opt/careerscout/careerscout.py" >/dev/null 2>&1; then
      setsid nohup python3 /opt/careerscout/careerscout.py >>/tmp/careerscout.log 2>&1 </dev/null &
      sleep 1
    fi
    if wmctrl -l 2>/dev/null | grep -qi careerscout; then
      wmctrl -r CareerScout -b add,maximized_vert,maximized_horz 2>/dev/null || true
      wmctrl -a CareerScout 2>/dev/null || true
    fi
    sleep 0.4
  done
}
setsid nohup bash -c "$(declare -f keeper); keeper" >>/tmp/careerscout.log 2>&1 </dev/null &
exit 0
