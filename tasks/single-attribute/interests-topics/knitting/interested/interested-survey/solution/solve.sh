#!/usr/bin/env bash
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"
harbor_run_agent
harbor_recover_file survey_result.json survey_result.json
harbor_pack_trace
