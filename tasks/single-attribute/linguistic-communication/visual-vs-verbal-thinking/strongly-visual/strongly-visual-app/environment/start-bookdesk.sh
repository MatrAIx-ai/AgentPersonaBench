#!/usr/bin/env bash
set -u
export DISPLAY=:1
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
export PLAYGROUND_OUTPUT_DIR="${PLAYGROUND_OUTPUT_DIR:-$ADHERENCE_OUTPUT_DIR}"
mkdir -p "$ADHERENCE_OUTPUT_DIR" 2>/dev/null || true
bringup() {
  export DISPLAY=:1
  for _ in $(seq 1 120); do [ -e /tmp/.X11-unix/X1 ] && break; sleep 1; done
  for _ in $(seq 1 4000); do
    if ! xdotool search --name BookDesk 2>/dev/null | grep -q .; then DISPLAY=:1 setsid nohup python3 /opt/bookdesk/app.py >>/tmp/bookdesk.log 2>&1 < /dev/null & sleep 2; fi
    for wid in $(xdotool search --name BookDesk 2>/dev/null); do xdotool windowraise "$wid" 2>/dev/null || true; xdotool windowactivate "$wid" 2>/dev/null || true; done
    for cid in $(xdotool search --class chromium 2>/dev/null; xdotool search --name 'about:blank' 2>/dev/null); do xdotool windowminimize "$cid" 2>/dev/null || true; done
    wmctrl -a BookDesk 2>/dev/null || true; sleep 0.4
  done
}
setsid nohup bash -c "$(declare -f bringup); ADHERENCE_OUTPUT_DIR='$ADHERENCE_OUTPUT_DIR' PLAYGROUND_OUTPUT_DIR='$PLAYGROUND_OUTPUT_DIR' bringup" >>/tmp/bookdesk.log 2>&1 < /dev/null &
for _ in $(seq 1 40); do xdotool search --name BookDesk 2>/dev/null | grep -q . && break; sleep 1; done
exit 0
