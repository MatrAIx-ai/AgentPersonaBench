#!/usr/bin/env bash
# The complete persona operates PerkPack on a Linux desktop through screenshots
# and coordinate clicks. The native app writes selection.json itself.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export ADHERENCE_PERSONA="${ADHERENCE_PERSONA:-p-ec140af52f}"
export HARBOR_EXTRA_AK="max_steps=40"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
harbor_recover_file selection.json selection.json
harbor_pack_trace
