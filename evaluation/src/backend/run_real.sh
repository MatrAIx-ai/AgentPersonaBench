#!/usr/bin/env bash
# run_real.sh -- launch Playground API in REAL mode (in-repo InteRecAgent + OpenAI).
#
# Thin wrapper over run_dev.sh: it pins the REAL-mode knobs (native ranker,
# recai_resources resource mode), then hands off to run_dev.sh which loads
# .env.local and execs uvicorn on the canonical project .venv (uv-managed
# Python 3.9 — see ../README.md).
#
# The local UI backend and the task-owned RecAI bridge share the .venv. The
# RecAI checkout resolves through recbot/paths.py inside the chatbot task API
# source directory.
#
# Prereqs:
#   - the project .venv provisioned per ../README.md (torch 1.13.1 CPU,
#     unirec, sentence-transformers 2.2.2, fastapi/pydantic v2, ...)
#   - OPENAI_API_KEY in .env.local (this app dir; gitignored, loaded by run_dev.sh)
#
set -euo pipefail

BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# REAL-mode knobs: native ranker + recai_resources resources (the only
# supported combination — see ../README.md.
export INTERECAGENT_RANKER_MODE="native"
export INTERECAGENT_RESOURCE_MODE="recai_resources"
export INTERECAGENT_TIMEOUT_SECONDS="${INTERECAGENT_TIMEOUT_SECONDS:-900}"

# HuggingFace / sentence-transformers caches default to ~/.cache. On first REAL
# run, sentence-transformers downloads thenlper/gte-base (~833 MB) there. If your
# home dir is space-constrained, redirect them by exporting HF_HOME /
# TRANSFORMERS_CACHE / SENTENCE_TRANSFORMERS_HOME in .env.local (this app dir,
# gitignored, loaded by run_dev.sh) — see ../README.md.
export TOKENIZERS_PARALLELISM=false

unset RECBOT_STUDIO_DEMO  # REAL mode: route turns to llm4crs, not the scripted demo.

echo "[run_real] ranker     : ${INTERECAGENT_RANKER_MODE}"
echo "[run_real] resources  : ${INTERECAGENT_RESOURCE_MODE}"
echo "[run_real] OPENAI key : (loaded from .env.local by run_dev.sh)"

# Hand off to run_dev.sh, which loads .env.local and execs uvicorn on the .venv.
exec bash "${BACKEND_DIR}/run_dev.sh"
