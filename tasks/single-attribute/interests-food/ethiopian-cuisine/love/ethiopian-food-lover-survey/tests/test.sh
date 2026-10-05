#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if ! python3 -c 'import yaml' >/dev/null 2>&1; then
  python3 -m pip install --disable-pip-version-check --no-cache-dir 'PyYAML==6.0.3' || \
    printf '%s\n' 'PyYAML installation failed; the verifier will report the missing dependency.' >&2
fi

export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${HARBOR_OUTPUT_DIR:-/app/output}}"
export ADHERENCE_VERIFIER_DIR="${ADHERENCE_VERIFIER_DIR:-${HARBOR_VERIFIER_DIR:-/logs/verifier}}"
exec python3 "$HERE/verifier.py"
