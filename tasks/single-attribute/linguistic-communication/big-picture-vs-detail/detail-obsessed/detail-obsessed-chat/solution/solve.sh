#!/usr/bin/env bash
# Solver — Big-picture vs detail = Detail-obsessed, CHAT env. The persona is run as
# a real AGENT: harbor's UserSimulator (persona-user-sim) drives the conversation,
# deciding each turn in character from the task's full v2.0 persona.yaml. It talks
# to a bot the task defines with a single prompt (input/bot.md) — a catering rep
# who pitches a popular-but-noncompliant package and only reveals a compliant
# alternative on explicit ask. All the plumbing lives in the infra
# (evaluation/src/chat_harness.py); this task just names its persona, its bot, and
# its scenario. Same four-env entry point (solve.sh) as survey/web/app.
#
# run_task.py provides: ADHERENCE_OUTPUT_DIR (where verifier.py reads
# transcript.json), ADHERENCE_ARM (arm id).
#
# Output: transcript.json (+ user_turns.json, generation.json).
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
ARM="${ADHERENCE_ARM:-opus-4-8}"

RUNTIME="$REPO_DIR/evaluation/src"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"

# The infra runs the whole chat: persona agent (user-sim) vs the task's prompt-bot,
# writing transcript.json + user_turns.json into OUTPUT_DIR for the verifier.
PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" -c "
from chat_harness import run_chat_adherence
run_chat_adherence('$TASK_DIR', '$OUTPUT_DIR', '$ARM')
"
