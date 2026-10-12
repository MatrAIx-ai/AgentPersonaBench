#!/usr/bin/env bash
# Solver — APP env. The persona operates Weeknight Table Desktop on a local CUA
# desktop by screenshot + coordinate click; the app writes order_result.json.
# Uses the harbor CUA agent (persona-computer-1). Boilerplate lives in
# evaluation/src/lib/harbor_solve.sh; this file only picks the CUA agent + recovers.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
BASE_IMAGE="matraix/shared-os-app-linux:local"
BASE_ENVDEF="$REPO_DIR/evaluation/src/environment/task-environments/application/shared-os-app-linux"
if ! docker image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
  docker build -q -t "$BASE_IMAGE" "$BASE_ENVDEF" >/dev/null
fi
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export HARBOR_EXTRA_AK="max_steps=40"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
harbor_recover_file order_result.json order_result.json
harbor_recover_dir solution solution
harbor_pack_trace
