#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Use the deps-carrying interpreter when the harness provides one: chat
# verifiers import llm_client -> provider SDKs a bare system python3 may lack.
exec "${RUNTIME_PYTHON:-python3}" "$HERE/verifier.py"
