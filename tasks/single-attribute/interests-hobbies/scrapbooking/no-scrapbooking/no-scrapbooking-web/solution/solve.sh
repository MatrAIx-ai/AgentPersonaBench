#!/usr/bin/env bash
# Solver — REAL WEB env. The persona operates the live page itself through the
# shared web agent (evaluation/src/web_agent.py): every step it sees the
# rendered page as text and picks one action, until it says it is done.
# solution/web.json says how the final page state becomes the verifier's input.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"
while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
export ADHERENCE_PERSONA="${ADHERENCE_PERSONA:-no_scrapbooking}"
source "$REPO_DIR/evaluation/src/lib/web_solve.sh"
web_run_agent
