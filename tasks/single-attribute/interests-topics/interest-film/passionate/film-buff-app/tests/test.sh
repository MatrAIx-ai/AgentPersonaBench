#!/usr/bin/env bash
# Film passionate, APP env
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The agent's order.json is under the artifacts output dir; harbor reads the
# reward from its own verifier dir (/logs/verifier). Point the verifier at both:
# read order.json from the output dir, write reward.txt/structured_output.json to
# the harbor verifier dir so the runner picks up the reward.
export ADHERENCE_OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-${HARBOR_OUTPUT_DIR:-/logs/artifacts}}"
export ADHERENCE_VERIFIER_DIR="${HARBOR_VERIFIER_DIR:-/logs/verifier}"
mkdir -p "$ADHERENCE_VERIFIER_DIR"

exec python3 "$HERE/verifier.py"
