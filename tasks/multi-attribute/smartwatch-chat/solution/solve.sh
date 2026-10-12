#!/usr/bin/env bash
# Solver — smartwatch configuration, CHAT env. The persona user-simulator talks
# to the task's store bot. The verifier judges only the persona's own turns.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
ARM="${ADHERENCE_ARM:-opus-4-8}"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"

PYTHONPATH="$REPO_DIR/evaluation/src" "$RUNTIME_PYTHON" -c "
from chat_harness import run_chat_adherence
run_chat_adherence('$TASK_DIR', '$OUTPUT_DIR', '$ARM')
"
"$RUNTIME_PYTHON" "$TASK_DIR/solution/record_chat.py" "$OUTPUT_DIR" "$ARM"
