#!/usr/bin/env bash
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"
while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do
  REPO_DIR="$(dirname "$REPO_DIR")"
done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"
mkdir -p "$OUTPUT_DIR"
export PYTHONUTF8=1
export PYTHONPATH="$REPO_DIR/evaluation/src${PYTHONPATH:+:$PYTHONPATH}"
exec "${RUNTIME_PYTHON:-python3}" "$TASK_DIR/solution/run_chat.py" "$TASK_DIR" "$OUTPUT_DIR" "${ADHERENCE_ARM:-opus-4-8}"
