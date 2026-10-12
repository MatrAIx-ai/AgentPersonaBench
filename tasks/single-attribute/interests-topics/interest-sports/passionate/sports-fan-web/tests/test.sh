#!/usr/bin/env bash
# Sports passionate, WEB env
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/verifier.py"
