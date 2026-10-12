#!/usr/bin/env bash
# Solver — Familiarity: Astronomy, APP env. The persona operates PeriodoScope (a
# native Tkinter GUI) on a local CUA desktop by screenshot + coordinate click;
# the app writes the submission to submission.json itself. Uses the harbor CUA
# agent (persona-computer-1) with max_steps=40. All the harbor/gateway/recovery
# boilerplate lives in evaluation/src/lib/harbor_solve.sh; this file only picks
# the CUA agent and names what to recover.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
# gpt-* arms have no native OpenAI computer-use model here; run the CUA agent
# through the generic litellm JSON harness (works with any vision model).
export HARBOR_EXTRA_AK="max_steps=60"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
harbor_recover_file submission.json submission.json
harbor_pack_trace
