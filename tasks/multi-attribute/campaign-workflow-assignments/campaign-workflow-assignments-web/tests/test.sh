#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ADHERENCE_OUTPUT_DIR="${PLAYGROUND_OUTPUT_DIR:-${ADHERENCE_OUTPUT_DIR:-${HARBOR_OUTPUT_DIR:-/app/output}}}"
export ADHERENCE_VERIFIER_DIR="${HARBOR_VERIFIER_DIR:-${ADHERENCE_VERIFIER_DIR:-/logs/verifier}}"
mkdir -p "$ADHERENCE_VERIFIER_DIR"
# Use the deps-carrying interpreter when the harness provides one: chat
# verifiers import llm_client -> provider SDKs a bare system python3 may lack.
exec "${RUNTIME_PYTHON:-python3}" "$HERE/verifier.py"
