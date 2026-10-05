#!/usr/bin/env bash
# Solver — codetesting, APP env. The persona operates CodeForge (a native Tkinter
# GUI), types a solution in the editor and submits; the app writes
# solution/solution.py itself. Uses the harbor CUA agent (persona-computer-1) with
# max_steps=40. All the harbor/gateway/recovery boilerplate lives in
# evaluation/src/lib/harbor_solve.sh; this file only picks the CUA agent and names
# what to recover.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export HARBOR_EXTRA_AK="max_steps=40"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
harbor_recover_dir solution solution
harbor_pack_trace
