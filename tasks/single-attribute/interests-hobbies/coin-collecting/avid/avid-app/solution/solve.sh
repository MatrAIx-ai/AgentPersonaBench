#!/usr/bin/env bash
# Native Linux GUI, driven by the shared persona-computer-1 Harbor helper.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"
while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do
  REPO_DIR="$(dirname "$REPO_DIR")"
done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export HARBOR_EXTRA_AK="max_steps=30"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"
harbor_run_agent
harbor_recover_file hobby_reservation.json hobby_reservation.json
harbor_pack_trace
