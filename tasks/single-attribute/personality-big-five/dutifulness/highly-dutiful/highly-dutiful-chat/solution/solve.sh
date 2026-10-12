#!/usr/bin/env bash
# Solver — Highly dutiful, CHAT env. The persona is run as a real AGENT: harbor's
# UserSimulator (persona-user-sim) drives the conversation in character from the
# task's full v2.0 persona.yaml, talking to a bot the task defines with one prompt
# (input/bot.md) — an easygoing, fun-chasing friend that keeps pushing them to blow
# off their commitments. A highly-dutiful persona should insist on keeping their word
# and honoring what they signed up for, resisting the pressure to flake or bend the
# rules without ever being told to be dutiful.
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
