#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Harbor uploads tests only after acting; rewards are separate from native answers.
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${HARBOR_OUTPUT_DIR:-/app/output}}"
export ADHERENCE_VERIFIER_DIR="${ADHERENCE_VERIFIER_DIR:-${HARBOR_VERIFIER_DIR:-/logs/verifier}}"
export ADHERENCE_ALLOW_PACKAGED_CHECK=1
mkdir -p "$ADHERENCE_VERIFIER_DIR"
exec python3 -B "$HERE/verifier.py"
