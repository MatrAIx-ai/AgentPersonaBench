#!/usr/bin/env bash
# Verifier entrypoint. Assumes solution/solve.sh (or a real agent run) wrote both
# arms to $ADHERENCE_OUTPUT_DIR/{anchor,contrast}/plan.json.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Use the deps-carrying interpreter: chat verifiers import llm_client -> anthropic,
# which a bare system python3 may lack. $RUNTIME_PYTHON is set by the runner/harness.
exec "${RUNTIME_PYTHON:-python3}" "$HERE/verifier.py"
