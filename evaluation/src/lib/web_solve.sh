#!/usr/bin/env bash
# Shared solver for `web` tasks. A task's solution/solve.sh is three lines:
#
#   #!/usr/bin/env bash
#   TASK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
#   REPO_DIR="$TASK_DIR"; while [ ! -d "$REPO_DIR/evaluation/src" ]; do REPO_DIR="$(dirname "$REPO_DIR")"; done
#   source "$REPO_DIR/evaluation/src/lib/web_solve.sh"; web_run_agent
#
# The persona drives the page itself through evaluation/src/web_agent.py: every
# step it sees the rendered page as text with numbered controls and chooses one
# action, until it declares the task done. The goal is the task's
# instruction.md; the task supplies only its page (input/site/), the persona
# role, and how to read the final state for its verifier (solution/web.json).
#
# Env in: ADHERENCE_OUTPUT_DIR, ADHERENCE_PERSONA, LLM_PROXY_URL, LLM_MODEL,
#         WEB_MAX_STEPS (optional, default 40), APB_WEB_OBS (hybrid | text,
#         default hybrid), RUNTIME_PYTHON (optional).
set -euo pipefail

: "${TASK_DIR:?web_solve.sh: caller must set TASK_DIR before sourcing}"
REPO_DIR="${REPO_DIR:-$TASK_DIR}"
while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do
  REPO_DIR="$(dirname "$REPO_DIR")"
done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"
WEB_IMAGE="matraix/shared-web-playwright:local"
WEB_ENVDEF="$REPO_DIR/evaluation/src/environment/task-environments/application/shared-web-playwright"
WEB_SPEC="$TASK_DIR/solution/web.json"

web_run_agent() {
  [ -f "$WEB_SPEC" ] || { echo "solve: $WEB_SPEC is missing" >&2; exit 2; }
  if ! docker image inspect "$WEB_IMAGE" >/dev/null 2>&1; then
    docker build -q -t "$WEB_IMAGE" "$WEB_ENVDEF" >/dev/null
  fi
  local role persona_sys
  role="$("$RUNTIME_PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1])).get("role") or "a user")' "$WEB_SPEC")"
  persona_sys="$(PYTHONPATH="$REPO_DIR" "$RUNTIME_PYTHON" -c \
    "import sys; from evaluation.src.persona import persona_system_prompt; print(persona_system_prompt(sys.argv[1], role=sys.argv[2]))" \
    "$TASK_DIR" "$role")"

  # The proxy listens on the host; on Docker Desktop (macOS) the container
  # reaches it through host.docker.internal instead of --network=host.
  local proxy="${LLM_PROXY_URL:-http://127.0.0.1:8991}"
  local net=(--network=host)
  if [ "$(uname -s)" = Darwin ]; then
    proxy="${proxy/127.0.0.1/host.docker.internal}"
    proxy="${proxy/localhost/host.docker.internal}"
    net=(--add-host=host.docker.internal:host-gateway)
  fi

  docker run --rm "${net[@]}" \
    -v "$REPO_DIR/evaluation/src/agent_client.py:/app/agent_client.py:ro" \
    -v "$REPO_DIR/evaluation/src/web_agent.py:/app/web_agent.py:ro" \
    -v "$TASK_DIR/instruction.md:/app/goal.md:ro" \
    -v "$WEB_SPEC:/app/web.json:ro" \
    -v "$TASK_DIR/input/site:/app/site:ro" \
    -v "$OUTPUT_DIR:/app/output" \
    -e LLM_PROXY_URL="$proxy" -e LLM_MODEL="${LLM_MODEL:-}" \
    -e ADHERENCE_PERSONA="${ADHERENCE_PERSONA:-}" -e PERSONA_SYS="$persona_sys" \
    -e WEB_MAX_STEPS="${WEB_MAX_STEPS:-40}" -e APB_WEB_OBS="${APB_WEB_OBS:-hybrid}" \
    "$WEB_IMAGE" python3 /app/web_agent.py --goal-file /app/goal.md --spec /app/web.json
}
