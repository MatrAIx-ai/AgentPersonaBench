#!/usr/bin/env bash
# Solver — Strict monotasker, CHAT env. The persona is run as a real AGENT: harbor's
# UserSimulator (persona-user-sim) drives the conversation in character from the
# task's full v2.0 persona.yaml, talking to a bot the task defines with one prompt
# (input/bot.md) — an eager, do-it-all friend that keeps pushing them to juggle
# everything at once. A strict-monotasker persona should insist on doing one thing
# at a time and protect their focus, resisting the juggle-everything pressure without
# ever being told to be a monotasker.
# All plumbing lives in the infra (evaluation/src/chat_harness.py); this task just
# names its persona, its bot, and its scenario. Same entry point as the other envs.
#
# run_task.py provides ADHERENCE_OUTPUT_DIR + ADHERENCE_ARM. Provider keys:
# the provider's native API key (see evaluation/configs/README.md).
#
# Output: user_turns.json = {"turns": [...]} (+ transcript.json).
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
