#!/usr/bin/env bash
# Launch CodeDesk on the CUA runtime's Xvfb display and keep it above Chromium.
set -u
export DISPLAY=:1
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/logs/artifacts}}"
export PLAYGROUND_OUTPUT_DIR="${PLAYGROUND_OUTPUT_DIR:-$ADHERENCE_OUTPUT_DIR}"
mkdir -p "$ADHERENCE_OUTPUT_DIR" 2>/dev/null || true

bringup() {
  export DISPLAY=:1
  for _ in $(seq 1 120); do [ -e /tmp/.X11-unix/X1 ] && break; sleep 1; done
  for _ in $(seq 1 4000); do
    if ! xdotool search --name CodeDesk 2>/dev/null | grep -q .; then
      DISPLAY=:1 setsid nohup python3 /opt/app/app.py >>/tmp/codedesk.log 2>&1 < /dev/null &
      sleep 2
    fi
    for window_id in $(xdotool search --name CodeDesk 2>/dev/null); do
      xdotool windowraise "$window_id" 2>/dev/null || true
      xdotool windowactivate "$window_id" 2>/dev/null || true
    done
    for browser_id in $(xdotool search --class chromium 2>/dev/null; xdotool search --name 'about:blank' 2>/dev/null); do
      xdotool windowminimize "$browser_id" 2>/dev/null || true
    done
    wmctrl -a CodeDesk 2>/dev/null || true
    sleep 0.4
  done
}
setsid nohup bash -c "$(declare -f bringup); ADHERENCE_OUTPUT_DIR='$ADHERENCE_OUTPUT_DIR' PLAYGROUND_OUTPUT_DIR='$PLAYGROUND_OUTPUT_DIR' bringup" \
  >>/tmp/codedesk.log 2>&1 < /dev/null &
for _ in $(seq 1 40); do
  xdotool search --name CodeDesk 2>/dev/null | grep -q . && break
  sleep 1
done
exit 0
