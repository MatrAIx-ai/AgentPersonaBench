#!/usr/bin/env bash
# Prefers calls, CHAT env
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Use the deps-carrying interpreter: chat verifiers import llm_client -> anthropic,
# which a bare system python3 may lack. $RUNTIME_PYTHON is set by the runner/harness.
exec "${RUNTIME_PYTHON:-python3}" "$HERE/verifier.py"
