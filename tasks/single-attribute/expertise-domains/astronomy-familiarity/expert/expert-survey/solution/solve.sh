#!/usr/bin/env bash
# Solver — SURVEY env. A real harbor agent runs in docker, reads instruction.md +
# /app/input/questionnaire.yaml, and writes /app/output/survey_result.json itself.
# All the harbor/gateway/recovery boilerplate lives in evaluation/src/lib/harbor_solve.sh;
# this file only names what to recover. No edits normally needed.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
harbor_recover_file report.json report.json
harbor_pack_trace
