#!/usr/bin/env bash
# Solver — Cognitive load capacity = Low, CHAT env. The persona is run as a real
# AGENT: harbor's UserSimulator (persona-user-sim) drives the conversation, deciding
# each turn in character from the task's full v2.0 persona.yaml. It talks to a bot
# the task defines with a single prompt (input/bot.md) — a photo-organizing
# assistant that keeps offering joint multi-criteria tagging. All the plumbing
# lives in the infra (evaluation/src/chat_harness.py); this task just names its
# persona, its bot, and its scenario. Same four-env entry point (solve.sh) as
# survey/app/web.
#
# run_task.py provides: ADHERENCE_OUTPUT_DIR (where verifier.py reads
# user_turns.json), ADHERENCE_ARM (arm id). Provider keys: the provider's
# native API key (see evaluation/configs/README.md).
#
# Output: user_turns.json = {"turns": [...]} (+ transcript.json).
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
ARM="${ADHERENCE_ARM:-opus-4-8}"

# $RUNTIME_PYTHON: a python with the vendored runtime's deps installed
# (pip install -r evaluation/src/runtime-meta/requirements.txt). Defaults to python3.
RUNTIME="$REPO_DIR/evaluation/src"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"

# The infra runs the whole chat: persona agent (user-sim) vs the task's prompt-bot,
# writing user_turns.json + transcript.json into OUTPUT_DIR for the verifier.
PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" -c "
from chat_harness import run_chat_adherence
run_chat_adherence('$TASK_DIR', '$OUTPUT_DIR', '$ARM')
"
