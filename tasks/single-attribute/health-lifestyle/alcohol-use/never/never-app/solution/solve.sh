#!/usr/bin/env bash
# Solver — APP env. The persona operates your native GUI on a local CUA desktop by
# screenshot + coordinate click; the app writes the result (order.json) itself.
# Uses the harbor CUA agent (persona-computer-1). Boilerplate lives in
# evaluation/src/lib/harbor_solve.sh; this file only picks the CUA agent + recovers.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export HARBOR_EXTRA_AK="max_steps=40"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
# CanteenOrder writes order.json itself on Place order; recover it for the verifier.
harbor_recover_file order.json order.json
harbor_recover_dir solution solution
harbor_pack_trace
