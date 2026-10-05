#!/usr/bin/env bash
# Solver — codetesting, CHAT env. The persona is run as a real AGENT: harbor's
# UserSimulator (persona-user-sim) drives the conversation in character from the
# task's full v2.0 persona.yaml. It uses a coding bot (defined by input/bot.md)
# the way a developer uses an AI coding tool: it states the bug, reads the
# returned code, and asks for revisions until the fix matches how IT likes code
# written. We keep the LAST parseable code the bot produced and write it to
# solution/solution.py for the rule-based style verifier. The persona's
# practices (writing tests, docstring-only documentation, a regression test for
# the reported defect) surface through the changes it requests — never by being
# told. Complexity lives in the infra (evaluation/src/chat_harness.py); this
# task just names its persona and bot.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
ARM="${ADHERENCE_ARM:-opus-4-8}"
RUNTIME="$REPO_DIR/evaluation/src"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"

PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" -c "
from chat_harness import run_chat_codegen
run_chat_codegen('$TASK_DIR', '$OUTPUT_DIR', '$ARM')
"
