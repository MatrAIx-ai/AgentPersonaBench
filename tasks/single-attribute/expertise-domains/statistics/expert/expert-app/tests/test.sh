#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ADHERENCE_VERIFIER_DIR="${ADHERENCE_VERIFIER_DIR:-/logs/verifier}"
exec python3 "$HERE/verifier.py"
