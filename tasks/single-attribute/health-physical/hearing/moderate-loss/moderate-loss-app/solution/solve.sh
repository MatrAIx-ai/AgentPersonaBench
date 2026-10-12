#!/usr/bin/env bash
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"
while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export HARBOR_EXTRA_AK="max_steps=60"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

EXPECTED_PERSONA_HASH="d436493affd28915e34f1bdd88faefed37487c99d2f93e76b77fc52532acc171"
PERSONA_HASH="$(python3 -c "import hashlib; print(hashlib.sha256(open('$TASK_DIR/persona.yaml','rb').read()).hexdigest())")"
if [ "$PERSONA_HASH" != "$EXPECTED_PERSONA_HASH" ]; then
  echo "persona hash does not match the audited task contract" >&2
  exit 1
fi

harbor_run_agent
harbor_recover_file preferences.json preferences.json
harbor_recover_file run_context.json run_context.json
harbor_recover_file interaction_trace.jsonl interaction_trace.jsonl
harbor_recover_dir solution solution
harbor_pack_trace
