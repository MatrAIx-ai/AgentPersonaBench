#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${RUNTIME_PYTHON:-python3}" "$HERE/verifier.py"
