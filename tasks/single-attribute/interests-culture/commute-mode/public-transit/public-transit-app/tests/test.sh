#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The app writes the enrollment artifact under Harbor's artifact output dir,
# while Harbor collects verifier rewards from /logs/verifier. Keep the two
# destinations explicit so both the inner Harbor result and the outer runner
# observe the same successful verification.
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${HARBOR_OUTPUT_DIR:-/app/output}}"
export ADHERENCE_VERIFIER_DIR="${HARBOR_VERIFIER_DIR:-/logs/verifier}"
mkdir -p "$ADHERENCE_VERIFIER_DIR"

exec python3 "$HERE/verifier.py"
