#!/usr/bin/env bash
# Solver — CHAT env. The persona is run as a real AGENT: harbor's UserSimulator
# drives the conversation in character from persona.yaml, talking to the bot this
# task defines (input/bot.md). All plumbing lives in evaluation/src/chat_harness.py.
# Output: user_turns.json = {"turns":[...]} (+ transcript.json). No edits normally needed.
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
ARM="${ADHERENCE_ARM:-opus-4-8}"
RUNTIME="$REPO_DIR/evaluation/src"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"

PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" "$TASK_DIR/solution/run_suite.py"
