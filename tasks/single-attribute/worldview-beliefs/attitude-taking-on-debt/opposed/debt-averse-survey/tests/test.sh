#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ADHERENCE_VERIFIER_DIR="${HARBOR_VERIFIER_DIR:-/logs/verifier}"
mkdir -p "$ADHERENCE_VERIFIER_DIR"
exec "${RUNTIME_PYTHON:-python3}" "$HERE/verifier.py"
