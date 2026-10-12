#!/usr/bin/env bash
# Launch the PeriodoScope native GUI on the CUA desktop and KEEP it in front.
#
# Two hard-won details:
# - The harbor CUA runtime brings its desktop up on DISPLAY :1 (and only AFTER
#   this healthcheck runs), so the first launch attempt usually dies with "no
#   display" — the keeper below relaunches until X is up.
# - The keeper must live in a FILE, not a `bash -c "$(declare -f ...)"` inline:
#   inline, the app path appears in the keeper's own argv and `pgrep -f` matches
#   the keeper itself, so the app is never relaunched.
set -u
export DISPLAY="${DISPLAY:-:1}"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${PLAYGROUND_OUTPUT_DIR:-/app/output}}"
mkdir -p "$ADHERENCE_OUTPUT_DIR"

cat > /tmp/pscope-keeper.sh <<'KEEPER'
export DISPLAY="${DISPLAY:-:1}"
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"
for _ in $(seq 1 7200); do
  if ! pgrep -f 'python3 /opt/periodoscope/periodoscope.py' >/dev/null 2>&1; then
    setsid nohup python3 /opt/periodoscope/periodoscope.py >>/tmp/periodoscope.log 2>&1 < /dev/null &
    sleep 1
  fi
  if wmctrl -l 2>/dev/null | grep -qi periodoscope; then
    wmctrl -r PeriodoScope -b add,maximized_vert,maximized_horz 2>/dev/null || true
    wmctrl -a PeriodoScope 2>/dev/null || true
  fi
  sleep 0.5
done
KEEPER
chmod +x /tmp/pscope-keeper.sh
setsid nohup bash /tmp/pscope-keeper.sh >>/tmp/periodoscope.log 2>&1 < /dev/null &

exit 0
