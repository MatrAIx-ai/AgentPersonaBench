#!/usr/bin/env bash
# Opt-in full native control. This script is never called by solution/solve.sh.
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
[ "${ADHERENCE_RUN_BLIND:-}" = 1 ] || { echo "Set ADHERENCE_RUN_BLIND=1 for this explicit control." >&2; exit 2; }
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"
while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do
  REPO_DIR="$(dirname "$REPO_DIR")"
done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export HARBOR_EXTRA_AK="max_steps=30"
# Construct exactly the normal native helper configuration and full persona.
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"
[ "$AGENT" = persona-computer-1 ] && [ "$HARBOR_PROVIDER" = anthropic ] || {
  echo "Only the audited native Anthropic computer-1 route is supported." >&2; exit 2;
}
export BLIND_APP_EVIDENCE_DIR="$OUTPUT_DIR"
[ "${#_EXTRA[@]}" = 2 ] && [ "${_EXTRA[0]}" = --extra-instruction-path ] || {
  echo "Native extra-instruction contract changed." >&2; exit 3;
}
"$RUNTIME_PYTHON" -B "$TASK_DIR/tests/blind_adapter.py" --prepare-extra \
  "${_EXTRA[1]}" "$OUTPUT_DIR/blind-extra-instruction.txt" "$TASK_DIR/persona.yaml"
_EXTRA=(--extra-instruction-path "$OUTPUT_DIR/blind-extra-instruction.txt")
harbor() {
  PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" -B "$TASK_DIR/tests/blind_adapter.py" --harbor "$@"
}
if [ "${BLIND_APP_PREPARE_ONLY:-}" = 1 ]; then
  echo "Prepared persona-omitted extra instructions; no Docker, provider, or agent run."
  exit 0
fi
harbor_run_agent
harbor_recover_file loan_plan.json loan_plan.json
harbor_pack_trace
