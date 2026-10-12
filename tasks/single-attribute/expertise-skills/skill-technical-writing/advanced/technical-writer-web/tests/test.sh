#!/usr/bin/env bash
# Technical writing advanced, WEB env
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/verifier.py"
