#!/usr/bin/env bash
# Solver — Attitude: Higher education = Enthusiast · Attitude: Subscription services = Opposed, APP env. The persona operates CourseTermThree (a native
# Tkinter GUI) on a local CUA desktop by screenshot + coordinate click; the app
# writes enrolments.json itself. Uses the harbor CUA agent
# (persona-computer-1) with max_steps=40. All the harbor/gateway/recovery
# boilerplate lives in evaluation/src/lib/harbor_solve.sh; this file only picks
# the CUA agent and names what to recover.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
export ADHERENCE_AGENT="${ADHERENCE_AGENT:-persona-computer-1}"
export HARBOR_EXTRA_AK="max_steps=40"
# shellcheck source=/dev/null
source "$REPO_DIR/evaluation/src/lib/harbor_solve.sh"

harbor_run_agent
harbor_recover_file enrolments.json enrolments.json
harbor_recover_dir solution solution
harbor_pack_trace
