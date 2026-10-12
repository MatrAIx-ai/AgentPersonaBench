#!/usr/bin/env bash
# Solver — Driving status = Cannot drive, CHAT env. The persona is run as a
# real AGENT: harbor's UserSimulator drives the conversation in character from
# the task's full v2.0 persona.yaml, talking to a bot the task defines with one
# prompt (input/bot.md) — a corporate travel desk that recommends driving the
# included rental car for every leg and pushes back once per decline. All plumbing lives in the infra
# (evaluation/src/chat_harness.py); this task just names its persona, its bot,
# and its scenario.
#
# run_task.py provides ADHERENCE_OUTPUT_DIR + ADHERENCE_ARM. Provider keys come
# from the standard env vars (ANTHROPIC_API_KEY / OPENAI_API_KEY / GEMINI_API_KEY).
#
# Output: user_turns.json = {"turns": [...]} (+ transcript.json, trace.zip).
set -euo pipefail
TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_DIR="$TASK_DIR"; while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
ARM="${ADHERENCE_ARM:-opus-4-8}"
RUNTIME="$REPO_DIR/evaluation/src"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"

# Paths go through the environment, not interpolated into the -c source, so a
# path with spaces/quotes cannot break or inject into the python snippet.
TASK_DIR="$TASK_DIR" OUTPUT_DIR="$OUTPUT_DIR" ARM="$ARM" \
PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" -c '
import os
from chat_harness import run_chat_adherence
run_chat_adherence(os.environ["TASK_DIR"], os.environ["OUTPUT_DIR"], os.environ["ARM"])
'
