#!/usr/bin/env bash
# Solver — finconsumer, CHAT env. The persona is run as a real AGENT: harbor's
# UserSimulator (persona-user-sim) holds a conversation in character from the
# task's full v2.0 persona.yaml with the venue concierge (defined by
# input/bot.md). The persona states preferences, reacts to the concierge's
# middle-tier nudge, and confirms exact option codes; the verifier scores the
# confirmed codes per axis. Complexity lives in the infra
# (evaluation/src/chat_harness.py); this task just names its persona and bot.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
ARM="${ADHERENCE_ARM:-opus-4-8}"
RUNTIME="$REPO_DIR/evaluation/src"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"

PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" -c "
from chat_harness import run_chat_adherence
run_chat_adherence('$TASK_DIR', '$OUTPUT_DIR', '$ARM')
"
