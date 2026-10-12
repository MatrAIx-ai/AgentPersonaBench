#!/usr/bin/env bash
#
# run_dev.sh — start the Playground backend (FastAPI + uvicorn) for local dev.
#
# This launches the API only. The Vite dev server for the React SPA is run
# separately (see the note at the bottom), and proxies `/api` to this process.
#
# What it does:
#   - Resolves the backend root and the eval package root regardless of the
#     directory you call it from.
#   - Puts the repo root, `environment/runtime`, `environment/agents`,
#     `packages/playground/src`, and `application/playground` on PYTHONPATH so
#     that `import harbor...`, `import matraix...`, `import playground...`, and
#     `import backend...` resolve in-process.
#   - Runs a SINGLE uvicorn worker. `--reload` is opt-in via RELOAD=1 because a
#     reload spawns a child process and breaks in-memory job state.
#
# Usage:
#   bash application/playground/backend/run_dev.sh
#   PORT=8765 RELOAD=1 bash .../backend/run_dev.sh
#
# Requirements: deps from requirements.txt installed in the canonical project
# .venv (the uv-managed Python 3.9 env — see ../README.md). This script
# execs uvicorn from that interpreter. The server boots and serves /api/health
# and /api/preflight, surfacing missing optional credentials via /api/preflight.

set -euo pipefail

# --- resolve paths -----------------------------------------------------------
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
EVAL_DIR="$(cd "${BACKEND_DIR}/.." && pwd)"  # application/playground
REPO_ROOT="$(cd "${EVAL_DIR}/../.." && pwd)"
PLAYGROUND_CORE_DIR="${REPO_ROOT}/packages/playground/src"
MATRAIX_SRC_DIR="${REPO_ROOT}/src"
MATRIX_AGENTS_DIR="${REPO_ROOT}/environment/agents"

# --- interpreter: $VENV/bin/python if VENV is set, else `python` on PATH -------
# (Activate your venv, or pass VENV=/path/to/venv.)
VENV_PY="${VENV:+${VENV}/bin/}python"
if ! command -v "${VENV_PY}" >/dev/null 2>&1; then
  echo "[run_dev] ERROR: python interpreter '${VENV_PY}' not found." >&2
  echo "[run_dev]        activate your venv, or set VENV=/path/to/venv (see docs/application.md § Playground App)." >&2
  exit 1
fi

# --- load local secrets/env (gitignored) -------------------------------------
# Put OPENAI_API_KEY and sidecar-specific settings
# in .env.local next to run_demo.sh (copy it from .env.local.example). It is
# gitignored and auto-loaded here so secrets never live on the command line.
ENV_LOCAL="${EVAL_DIR}/.env.local"
if [[ -f "${ENV_LOCAL}" ]]; then
  echo "[run_dev] loading ${ENV_LOCAL}"
  set -a; source "${ENV_LOCAL}"; set +a
fi

# --- config (overridable via env) --------------------------------------------
PORT="${PORT:-8765}"
HOST="${HOST:-127.0.0.1}"
APP="backend.api.app:app"

# Make `backend`, `playground`, `harbor`, and `matraix` importable.
export PYTHONPATH="${REPO_ROOT}:${MATRAIX_SRC_DIR}:${REPO_ROOT}/environment/runtime:${MATRIX_AGENTS_DIR}:${PLAYGROUND_CORE_DIR}:${EVAL_DIR}${PYTHONPATH:+:${PYTHONPATH}}"
export MATRIX_HARBOR_COMMAND="${MATRIX_HARBOR_COMMAND:-uv run python -m harbor.cli.main run}"

RELOAD_FLAG=""
if [[ "${RELOAD:-0}" == "1" ]]; then
  RELOAD_FLAG="--reload"
  echo "[run_dev] WARNING: --reload uses a worker subprocess; the in-process" >&2
  echo "[run_dev]          in-memory job state will reset on every change." >&2
fi

echo "[run_dev] python      : ${VENV_PY}"
echo "[run_dev] backend dir : ${BACKEND_DIR}"
echo "[run_dev] PYTHONPATH  : ${REPO_ROOT}:${MATRAIX_SRC_DIR}:${REPO_ROOT}/environment/runtime:${MATRIX_AGENTS_DIR}:${PLAYGROUND_CORE_DIR}:${EVAL_DIR}"
echo "[run_dev] catalog     : ${INTERECAGENT_CATALOG_PATH:-(bundle default)}"
echo "[run_dev] serving     : http://${HOST}:${PORT}  (app ${APP})"
echo "[run_dev] harbor cmd  : ${MATRIX_HARBOR_COMMAND}"
echo "[run_dev] frontend    : in another terminal, run:"
echo "[run_dev]                 cd ${EVAL_DIR}/frontend && npm install && npm run dev"
echo "[run_dev]               then open http://localhost:5173 (it proxies /api here)."

# --- launch (single worker, on the .venv interpreter) ------------------------
exec "${VENV_PY}" -m uvicorn "${APP}" \
  --host "${HOST}" \
  --port "${PORT}" \
  --workers 1 \
  ${RELOAD_FLAG}
