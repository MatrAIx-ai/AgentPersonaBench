#!/usr/bin/env bash
# Solver — Risk-seeking, APP env. The persona operates BullVantage (a native
# Tkinter GUI) on a local CUA desktop by screenshot + coordinate click; the app
# writes the chosen holdings to order.json itself. Uses the harbor CUA agent
# (persona-computer-1) with max_steps=40. All the harbor/gateway/recovery
# boilerplate lives in evaluation/src/lib/harbor_solve.sh; this file only picks
# the CUA agent and names what to recover.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export HARBOR_EXTRA_AK="max_steps=40"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
# A missing agent artifact must not abort the run under `set -e` (recover_file
# returns 1 when the file is absent); fall through so the verifier scores 0.
harbor_recover_file order.json order.json || true
harbor_recover_dir solution solution
harbor_pack_trace
