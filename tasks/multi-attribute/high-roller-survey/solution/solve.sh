#!/usr/bin/env bash
# Solver — high-roller, SURVEY env. A real harbor agent (default
# persona-claude-code) runs in docker, reads instruction.md +
# /app/input/questionnaire.yaml, and writes /app/output/survey_result.json
# itself — a genuine trajectory + trace. All the harbor/gateway/recovery
# boilerplate lives in evaluation/src/lib/harbor_solve.sh; this file only
# names what to recover.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
# A missing agent artifact must not abort the run under `set -e` (recover_file
# returns 1 when the file is absent); fall through so the verifier scores 0.
harbor_recover_file survey_result.json survey_result.json || true
harbor_pack_trace
