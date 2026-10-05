#!/usr/bin/env bash
# Solver — Power-status multi-check, SURVEY env. A real harbor agent (default
# persona-claude-code) runs in docker, reads instruction.md + /app/input/questionnaire.yaml,
# and writes /app/output/survey_result.json itself — a genuine trajectory + trace. All the
# harbor/gateway/recovery boilerplate lives in evaluation/src/lib/harbor_solve.sh;
# this file only names what to recover.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
harbor_recover_file survey_result.json survey_result.json
harbor_pack_trace
