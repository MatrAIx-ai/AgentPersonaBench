#!/usr/bin/env bash
# Shared harbor solver library for APB tasks (app / survey — any env whose agent
# runs inside a harbor docker trial). SOURCE this from a task's solution/solve.sh;
# it collapses ~90 lines of boilerplate (runtime location, arm→model mapping,
# persona rendering, `harbor run`, trial recovery, trace.zip) into
# a couple of function calls, so a task's solve.sh stays ~15 lines.
#
# Contract with the caller (a task solve.sh):
#   - Before sourcing: nothing required.
#   - After sourcing: TASK_DIR, REPO_DIR, OUTPUT_DIR, ARM, PROVIDER, MODEL, AGENT
#     are set and the `harbor` function is defined.
#   - Then call:  harbor_run_agent        # runs the agent in a docker trial
#                 harbor_recover_file <container-rel-path> <dest-name>   # copy an
#                     agent-written artifact out of the trial (repeatable)
#                 harbor_recover_dir  <container-rel-dir>  <dest-dir>    # copy a dir
#                 harbor_pack_trace                                      # trace.zip
#   The temporary harbor job dir is auto-removed on exit (EXIT trap) — the caller
#   never sees the raw job; only the recovered artifacts land in OUTPUT_DIR.
#
# Env in:  ADHERENCE_OUTPUT_DIR, ADHERENCE_ARM, ADHERENCE_AGENT (optional),
#          RUNTIME_PYTHON (optional), RUNTIME_HOME (optional).
set -euo pipefail

# --- paths -------------------------------------------------------------------
# TASK_DIR is the dir of the *calling* solve.sh's parent (…/<task>/), resolved by
# the caller before sourcing (BASH_SOURCE[0] here would point at this lib). The
# caller sets TASK_DIR; we only default REPO_DIR/OUTPUT_DIR/ARM from it.
: "${TASK_DIR:?harbor_solve.sh: caller must set TASK_DIR before sourcing}"
REPO_DIR="${REPO_DIR:-$TASK_DIR}"
while [ "$REPO_DIR" != "/" ] && [ ! -d "$REPO_DIR/evaluation/src" ]; do
  REPO_DIR="$(dirname "$REPO_DIR")"
done
OUTPUT_DIR="${ADHERENCE_OUTPUT_DIR:-/app/output}"; mkdir -p "$OUTPUT_DIR"
ARM="${ADHERENCE_ARM:-opus-4-8}"

# --- locate the harbor runtime ----------------------------------------------
RUNTIME="$REPO_DIR/evaluation/src"
RUNTIME_PYTHON="${RUNTIME_PYTHON:-python3}"
if [ -d "$RUNTIME/harbor" ]; then
  harbor() { PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" -m harbor.cli.main "$@"; }
elif [ -n "${RUNTIME_HOME:-}" ] && [ -x "$RUNTIME_HOME/.venv/bin/harbor" ]; then
  harbor() { "$RUNTIME_HOME/.venv/bin/harbor" "$@"; }
elif [ -x "$(cd "$REPO_DIR/.." && pwd)/MatrAIx-Persona-8B/.venv/bin/harbor" ]; then
  RUNTIME_HOME="$(cd "$REPO_DIR/.." && pwd)/MatrAIx-Persona-8B"
  harbor() { "$RUNTIME_HOME/.venv/bin/harbor" "$@"; }
else
  echo "solve: no harbor runtime (install evaluation/src deps, or set RUNTIME_HOME)" >&2
  exit 3
fi

# --- arm -> provider + model -------------------------------------------------
# The MODEL is the single source of truth from configs/<arm>.json, exported by
# run_task.py as LLM_MODEL. Do NOT hardcode a model here — a per-arm literal
# silently overrode the config and made every envelope mislabel its model
# (opus arm recorded as opus, actually run as sonnet). We ONLY derive PROVIDER
# (which endpoint family to wire), preferring the runner's LLM_PROVIDER.
MODEL="${LLM_MODEL:-}"
if [ -z "$MODEL" ]; then
  echo "solve: LLM_MODEL is unset — run_task.py must export it from configs/<arm>.json" >&2
  exit 2
fi
PROVIDER="${LLM_PROVIDER:-}"
if [ -z "$PROVIDER" ]; then
  case "$ARM" in
    opus-4-8|claude)         PROVIDER=anthropic ;;
    gpt-5-6-sol|gpt)         PROVIDER=openai ;;
    gemini-3-7-flash|gemini) PROVIDER=gemini ;;
    *) echo "solve: unknown arm '$ARM' and no LLM_PROVIDER set" >&2; exit 2 ;;
  esac
fi
# --- agent selection: the agent must speak the arm's protocol -----------------
# An explicit ADHERENCE_AGENT always wins (app tasks pin persona-computer-1).
# Otherwise pick by provider: persona-claude-code is a Claude Code CLI and cannot
# drive a GPT, Gemini, Qwen or GLM arm — it exits immediately without writing the
# artifact, which used to surface as a behavioural score of 0 rather than as the
# infrastructure failure it is.
AGENT="${ADHERENCE_AGENT:-}"
if [ -z "$AGENT" ]; then
  case "$PROVIDER" in
    anthropic)                    AGENT=persona-claude-code ;;
    openai)                       AGENT=persona-codex ;;
    gemini)                       AGENT=persona-gemini-cli ;;
    dashscope|zai|openrouter|azure|deepseek|xai) AGENT=persona-openhands-sdk ;;
    *)                            AGENT=persona-claude-code ;;
  esac
fi

# --- OpenAI-compatible arms: LiteLLM model string + endpoint -----------------
# Runs for ANY agent, not just the one chosen above, because app tasks pin
# persona-computer-1 explicitly and still need the model rewritten.
#
# HARBOR_PROVIDER is what `--ak provider=` receives. Agents that do not take a
# `provider` kwarg ignore it (BaseAgent absorbs extra kwargs); computer-1 uses it
# to pick its harness, and `litellm` selects the generic screenshot+strict-JSON
# harness that drives any vision model without a native computer-use tool. Its
# own registry only knows litellm/anthropic/bedrock/gemini/openai, so passing a
# raw `zai` here is what made app trials die with "Unknown computer-1 provider".
HARBOR_PROVIDER="$PROVIDER"
case "$PROVIDER" in
  dashscope|zai|openrouter|azure|deepseek|xai)
    # Model string and endpoint come from the one registry in
    # evaluation/src/openai_compat.py, so this file holds no vendor URLs.
    _COMPAT=$(PYTHONPATH="$RUNTIME" "$RUNTIME_PYTHON" - "$PROVIDER" "$MODEL" <<'PYEOF'
import sys
import openai_compat
provider, model = sys.argv[1], sys.argv[2]
bare = model.split("/", 1)[1] if "/" in model else model

# Prefer LiteLLM's own name for the provider: it then carries the correct
# api_base, the right key env var, and - the part that matters for computer-1 -
# real `supports_vision` metadata, so the screenshot harness can refuse a
# text-only model instead of failing at the first screenshot. `zai/glm-5.3-flash`
# and `dashscope/qwen3-vl-plus` resolve this way. A provider LiteLLM does not
# know (a self-hosted gateway) falls back to its openai/ route plus an explicit
# base URL, where the metadata gate is skipped and the API is the arbiter.
native = False
if provider != "azure":
    try:
        from litellm import get_llm_provider
        _, resolved, _, _ = get_llm_provider(model="%s/%s" % (provider, bare))
        native = resolved == provider
    except Exception:
        native = False

print("%s/%s" % (provider if native else "openai", bare))
# On the native route LiteLLM already knows the vendor endpoint, so only an
# endpoint the operator actually configured is forced into the environment -
# a private or regional deployment (an Alibaba MaaS host, a self-hosted
# gateway) must win over LiteLLM's built-in default. The fallback route has no
# built-in default to fall back to, so it always needs one.
print(openai_compat.explicit_base_url_for(provider) if native
      else openai_compat.base_url_for(provider))
print(openai_compat.api_key_for(provider))
print("native" if native else "compat")
PYEOF
    ) || { echo "solve: could not resolve the $PROVIDER endpoint" >&2; exit 2; }
    MODEL=$(printf '%s\n' "$_COMPAT" | sed -n 1p)
    _COMPAT_BASE=$(printf '%s\n' "$_COMPAT" | sed -n 2p)
    _COMPAT_KEY=$(printf '%s\n' "$_COMPAT" | sed -n 3p)
    _COMPAT_ROUTE=$(printf '%s\n' "$_COMPAT" | sed -n 4p)
    if [ -z "$_COMPAT_KEY" ]; then
      echo "solve: no API key for provider '$PROVIDER' — see evaluation/src/openai_compat.py" >&2
      exit 2
    fi
    [ -n "$_COMPAT_BASE" ] && export LLM_BASE_URL="$_COMPAT_BASE"
    # OpenHands resolves the key for the model's LiteLLM provider first and only
    # then falls back to LLM_API_KEY, so export both. On the openai/ fallback the
    # provider var must also be set, or an ambient OPENAI_API_KEY meant for real
    # OpenAI would be sent to this endpoint and 401.
    export LLM_API_KEY="$_COMPAT_KEY"
    case "$PROVIDER" in
      zai)       export ZAI_API_KEY="$_COMPAT_KEY" ;;
      dashscope) export DASHSCOPE_API_KEY="$_COMPAT_KEY" ;;
      azure)     export AZURE_API_KEY="$_COMPAT_KEY" ;;
      deepseek)  export DEEPSEEK_API_KEY="$_COMPAT_KEY" ;;
      xai)       export XAI_API_KEY="$_COMPAT_KEY" ;;
    esac
    # LLM_BASE_URL is this repo's own convention; LiteLLM has never heard of it.
    # On the NATIVE route LiteLLM resolves the endpoint from the model prefix
    # alone — `dashscope/*` is hardcoded to the PUBLIC dashscope host — so a key
    # issued for a private deployment (an Alibaba MaaS endpoint) is sent to the
    # wrong host and every harbor trial dies with "Incorrect API key provided",
    # after the environment has already built. LiteLLM does read the provider's
    # own *_API_BASE var, so mirror the resolved endpoint into it.
    if [ -n "$_COMPAT_BASE" ]; then
      case "$PROVIDER" in
        zai)        export ZAI_API_BASE="$_COMPAT_BASE" ;;
        dashscope)  export DASHSCOPE_API_BASE="$_COMPAT_BASE" ;;
        openrouter) export OPENROUTER_API_BASE="$_COMPAT_BASE" ;;
        azure)      export AZURE_API_BASE="$_COMPAT_BASE" ;;
        deepseek)   export DEEPSEEK_API_BASE="$_COMPAT_BASE" ;;
        xai)        export XAI_API_BASE="$_COMPAT_BASE" ;;
      esac
    fi
    [ "$_COMPAT_ROUTE" = "compat" ] && export OPENAI_API_KEY="$_COMPAT_KEY"
    export LLM_MODEL="$MODEL"
    HARBOR_PROVIDER=litellm
    if [ "$AGENT" = "persona-computer-1" ]; then
      echo "solve: computer-1 generic harness — provider=litellm model=$MODEL base=${LLM_BASE_URL:-<default>}" >&2
      echo "solve: this harness is screenshot-driven; the model must accept image input." >&2
      echo "solve: if LiteLLM reports it vision-less, set ADHERENCE_ENABLE_IMAGES=1 to override." >&2
    fi
    ;;
esac

# --- one harness for every vendor ---------------------------------------------
# APB compares MODELS, so every arm must be driven by the same agent code on a
# surface. Picking the agent by vendor (claude-code / codex / gemini-cli on
# survey; each vendor's native computer-use tool on app) made a surface score
# part model, part harness: gemini-cli also searched the web on survey, native
# Gemini computer use thought at its default (high), and the azure GPT arms ran
# the generic loop while gpt-6-astra ran OpenAI's native one. In the default
# unified mode every vendor goes through LiteLLM: openhands-sdk on survey and
# computer-1's generic screenshot+JSON loop on app, the path the
# OpenAI-compatible arms above already take. LiteLLM also translates the suite's
# reasoning_effort into each vendor's own thinking field, so effort matches too.
# APB_HARNESS=native restores the per-vendor agents, to reproduce earlier runs.
APB_HARNESS="${APB_HARNESS:-unified}"
case "$APB_HARNESS" in
  unified|native) ;;
  *) echo "solve: APB_HARNESS must be 'unified' or 'native', got '$APB_HARNESS'" >&2; exit 2 ;;
esac
if [ "$APB_HARNESS" = unified ]; then
  [ -z "${ADHERENCE_AGENT:-}" ] && AGENT=persona-openhands-sdk
  case "$PROVIDER" in
    gemini)
      if [ "$(printf '%s' "${GOOGLE_GENAI_USE_VERTEXAI:-}" | tr '[:upper:]' '[:lower:]')" = true ]; then
        # Vertex AI on a GCP project (application-default credentials, no key).
        export VERTEXAI_PROJECT="${GOOGLE_CLOUD_PROJECT:?GOOGLE_CLOUD_PROJECT is required when GOOGLE_GENAI_USE_VERTEXAI=true}"
        export VERTEXAI_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"
        MODEL="vertex_ai/${MODEL#*/}"
        # computer-1 runs on the host and LiteLLM reads the ADC file itself. An
        # agent inside the task container gets the same credentials through
        # LiteLLM's VERTEXAI_CREDENTIALS (openhands_sdk forwards it). Vertex's
        # OpenAI-compatible endpoint is no substitute: it drops Gemini 3's
        # thought signatures, and the second tool call of a turn is rejected.
        _adc="${GOOGLE_APPLICATION_CREDENTIALS:-$HOME/.config/gcloud/application_default_credentials.json}"
        [ -f "$_adc" ] || { echo "solve: no Vertex credentials at $_adc (gcloud auth application-default login)" >&2; exit 2; }
        export VERTEXAI_CREDENTIALS="$(cat "$_adc")"
      else
        [ -z "${GEMINI_API_KEY:-}" ] && [ -n "${GOOGLE_API_KEY:-}" ] && export GEMINI_API_KEY="$GOOGLE_API_KEY"
        if [ -z "${GEMINI_API_KEY:-}" ]; then
          echo "solve: GEMINI_API_KEY is unset — the unified harness calls gemini through LiteLLM (or set GOOGLE_GENAI_USE_VERTEXAI=true)" >&2
          exit 2
        fi
        MODEL="gemini/${MODEL#*/}"
      fi
      export LLM_MODEL="$MODEL"
      HARBOR_PROVIDER=litellm
      ;;
    anthropic|openai)
      _KEY_VAR=$(printf '%s' "$PROVIDER" | tr '[:lower:]' '[:upper:]')_API_KEY
      if [ -z "${!_KEY_VAR:-}" ]; then
        echo "solve: $_KEY_VAR is unset — the unified harness calls $PROVIDER through LiteLLM" >&2
        exit 2
      fi
      MODEL="$PROVIDER/${MODEL#*/}"
      export LLM_MODEL="$MODEL"
      HARBOR_PROVIDER=litellm
      ;;
  esac
  echo "solve: unified harness — agent=$AGENT provider=$HARBOR_PROVIDER model=$MODEL" >&2
fi

# Agents authenticate with native provider keys (ANTHROPIC_API_KEY /
# OPENAI_API_KEY / GEMINI_API_KEY) already present in the environment. No gateway
# overlay or --ae injection is needed; these arrays stay empty.
_OVERLAY_ARGS=(); _AE_ARGS=()

# --- temp job dir + cleanup --------------------------------------------------
# harbor MUST write a job dir; we treat it as a throwaway staging area and remove
# it on exit so the raw job never accumulates in /tmp. Only recovered artifacts
# survive, in OUTPUT_DIR. (Set HARBOR_KEEP_JOB=1 to keep it for debugging.)
_JOBS_DIR="$(mktemp -d /tmp/pb_jobs_XXXX)"
_PROMPT_DIR="$(mktemp -d /tmp/pb_persona_XXXX)"
_cleanup() {
  harbor_pack_trace
  [ -n "${HARBOR_KEEP_JOB:-}" ] || rm -rf "$_JOBS_DIR" 2>/dev/null || true
  rm -rf "$_PROMPT_DIR" 2>/dev/null || true
  [ -n "${_OVERLAY:-}" ] && rm -f "$_OVERLAY" 2>/dev/null || true
}
trap _cleanup EXIT

# --- render persona prompt (extra instruction) -------------------------------
PYTHONPATH="$REPO_DIR/evaluation/src" python3 -c "
from persona import write_persona_prompt_file
write_persona_prompt_file('$TASK_DIR', '$_PROMPT_DIR')" >/dev/null 2>&1 || true
if [ "$AGENT" = "persona-computer-1" ] && [ -f "$_PROMPT_DIR/persona_prompt.txt" ]; then
  cat >> "$_PROMPT_DIR/persona_prompt.txt" <<'EOF'

Environment constraint: interact only with the visible application UI using screenshots, clicks, scrolling, and normal text entry. Do not use view-source, developer tools, DOM inspection, shell commands, or filesystem inspection.
EOF
fi
_EXTRA=(); [ -f "$_PROMPT_DIR/persona_prompt.txt" ] && _EXTRA=(--extra-instruction-path "$_PROMPT_DIR/persona_prompt.txt")

# --- run the agent -----------------------------------------------------------
# Extra agent kwargs a caller wants (e.g. app's max_steps=40) go in
# HARBOR_EXTRA_AK as space-separated "key=value" tokens; each is passed as its own
# `--ak key=value` (harbor rejects a bare "key=value" without the flag).
# NOTE: tokens are split on whitespace (IFS), so a VALUE must not contain spaces
# — `max_steps=40` works, `label=two words` does not. Any token missing an `=` is
# rejected loudly (stderr) and skipped rather than silently corrupting the args.
# harbor_ensure_base_images — build any shared base image the task's own
# environment/Dockerfile builds FROM, when it is not present locally.
#
# App environments start `FROM matraix/<name>:local`, an image assembled from
# evaluation/src/environment/task-environments/application/<name>. It exists in
# no registry, so on a fresh machine `docker compose build` fails with
#   pull access denied, repository does not exist
# and the trial reports "agent produced no artifact" — infrastructure wearing the
# costume of a behavioural failure. The web solvers already build their own base
# image on first use; this does the same for every harbor-backed task.
harbor_ensure_base_images() {
  local dockerfile="$TASK_DIR/environment/Dockerfile"
  [ -f "$dockerfile" ] || return 0
  local image name envdef
  for image in $(sed -n 's|^[[:space:]]*FROM[[:space:]]\{1,\}\(matraix/[A-Za-z0-9._-]\{1,\}:local\).*|\1|p' "$dockerfile"); do
    docker image inspect "$image" >/dev/null 2>&1 && continue
    name="${image#matraix/}"; name="${name%:local}"
    envdef="$REPO_DIR/evaluation/src/environment/task-environments/application/$name"
    if [ ! -d "$envdef" ]; then
      echo "solve: $image is missing and no definition at $envdef" >&2
      return 1
    fi
    echo "solve: building missing base image $image from $name (first run only, several minutes)" >&2
    if ! docker build -q -t "$image" "$envdef" >/dev/null; then
      echo "solve: failed to build base image $image" >&2
      return 1
    fi
  done
  return 0
}

harbor_run_agent() {
  harbor_ensure_base_images || {
    echo "solve: cannot run without the task's base image" >&2
    exit 1
  }
  local extra_ak=()
  if [ -n "${HARBOR_EXTRA_AK:-}" ]; then
    local _kw
    for _kw in $HARBOR_EXTRA_AK; do
      case "$_kw" in
        *=*) extra_ak+=(--ak "$_kw") ;;
        *)   echo "solve: ignoring malformed HARBOR_EXTRA_AK token '$_kw' (expected key=value, values must not contain spaces)" >&2 ;;
      esac
    done
  fi
  # Do NOT swallow the exit code — a failed run must not masquerade as an empty
  # success. We capture it, warn, and let recovery report "no artifact".
  local rc=0
  # Bash 3.2 (the macOS system Bash) treats an empty-array expansion as an
  # unbound variable under `set -u`. Build one non-empty argv array and append
  # optional groups only when populated, so survey/native-key runs work on both
  # Bash 3.2 and modern Bash without weakening nounset globally.
  local harbor_args=(run -a "$AGENT" -m "$MODEL" -o "$_JOBS_DIR"
    --ak provider="$HARBOR_PROVIDER" --ak persona_path="$TASK_DIR/persona.yaml")
  # reasoning_effort goes straight into the provider call, and not every model
  # accepts it: glm-5.3-flash answers `ZaiException - Invalid API parameter` and
  # the whole app trial dies before the agent takes a single screenshot. An arm
  # whose model rejects it sets "forward_reasoning_effort": false in its config.
  if [ -n "${ADHERENCE_EFFORT:-}" ] && [ "${ADHERENCE_FORWARD_EFFORT:-1}" = "1" ]; then
    harbor_args+=(--ak "reasoning_effort=$ADHERENCE_EFFORT")
  fi
  # computer-1 refuses a model LiteLLM's metadata calls vision-less. A model it
  # simply does not know (anything behind a custom base URL) passes unchecked.
  # This forces the issue when the metadata is wrong or absent.
  [ -z "${ADHERENCE_ENABLE_IMAGES:-}" ] || harbor_args+=(--ak "enable_images=true")
  # Without this computer-1 falls back to its own default temperature (0.7),
  # so the app surface would sample the arm differently from survey/chat/web.
  # computer-1 still drops it for models that reject an explicit temperature.
  if [ "$AGENT" = "persona-computer-1" ] && [ -n "${ADHERENCE_TEMPERATURE:-}" ]; then
    harbor_args+=(--ak "temperature=$ADHERENCE_TEMPERATURE")
  fi
  # computer-1 takes the endpoint as a real constructor argument, which beats
  # relying on LiteLLM picking up the *_API_BASE var above: it is explicit, and
  # it covers a provider whose env var LiteLLM does not consult. Only computer-1
  # is given it — other agents resolve their own endpoint, and an unexpected
  # kwarg is silently absorbed by BaseAgent rather than rejected, which would
  # hide a typo here instead of surfacing it.
  if [ "$AGENT" = "persona-computer-1" ] && [ -n "${LLM_BASE_URL:-}" ]; then
    harbor_args+=(--ak "api_base=$LLM_BASE_URL")
  fi
  [ "${#extra_ak[@]}" -eq 0 ] || harbor_args+=("${extra_ak[@]}")
  harbor_args+=(-p "$TASK_DIR" -e docker)
  [ "${#_EXTRA[@]}" -eq 0 ] || harbor_args+=("${_EXTRA[@]}")
  [ "${#_OVERLAY_ARGS[@]}" -eq 0 ] || harbor_args+=("${_OVERLAY_ARGS[@]}")
  [ "${#_AE_ARGS[@]}" -eq 0 ] || harbor_args+=("${_AE_ARGS[@]}")
  harbor "${harbor_args[@]}" || rc=$?
  if [ "$rc" -ne 0 ]; then
    echo "solve: harbor run exited $rc (agent=$AGENT arm=$ARM); recovery may find no artifact" >&2
  fi
  # Resolve the newest trial dir for this task so recovery helpers can use it.
  local task_name task_slug
  task_name="$(grep -m1 '^name' "$TASK_DIR/task.toml" | sed 's/.*"\(.*\)".*/\1/; s#.*/##')"
  # Harbor names the trial directory from the task folder slug, while task.toml
  # may use a namespaced display name (for example statistics-expert-survey).
  # Resolve by the folder slug first, then retain the legacy display-name
  # fallback for older tasks whose two names match.
  task_slug="$(basename "$TASK_DIR")"
  # Match Harbor's TrialConfig.generate_trial_name() normalization.
  task_slug="${task_slug:0:32}"
  while [[ "$task_slug" == *[-_] ]]; do
    task_slug="${task_slug%?}"
  done
  _TRIAL="$(ls -dt "$_JOBS_DIR"/*/"${task_slug}"__*/ 2>/dev/null | head -1 || true)"
  if [ -z "$_TRIAL" ]; then
    _TRIAL="$(ls -dt "$_JOBS_DIR"/*/"${task_name}"__*/ 2>/dev/null | head -1 || true)"
  fi
  if [ -z "$_TRIAL" ]; then
    echo "solve: no harbor trial produced for '$task_name' (agent failed to run)" >&2
  elif [ -f "$_TRIAL/result.json" ]; then
    # Harbor agents call providers directly, bypassing the host LLM proxy. Extract
    # only aggregate usage before the temporary job is deleted; do not retain the
    # full result, which may contain rollout details.
    "$RUNTIME_PYTHON" - "$_TRIAL/result.json" "$OUTPUT_DIR/harbor_usage.json" "$OUTPUT_DIR/harbor_diagnostics.json" <<'PY' || true
import json
import os
import sys
from datetime import datetime
from pathlib import Path

result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
contexts = []
if isinstance(result.get("agent_result"), dict):
    contexts.append(result["agent_result"])
else:
    contexts.extend(
        step["agent_result"] for step in result.get("step_results") or []
        if isinstance(step.get("agent_result"), dict)
    )

def total(key):
    values = [context[key] for context in contexts if isinstance(context.get(key), (int, float))]
    return sum(values) if values else None

def elapsed(timing):
    if not isinstance(timing, dict) or not timing.get("started_at") or not timing.get("finished_at"):
        return None
    start = datetime.fromisoformat(timing["started_at"].replace("Z", "+00:00"))
    finish = datetime.fromisoformat(timing["finished_at"].replace("Z", "+00:00"))
    return max(0.0, (finish - start).total_seconds())

latencies = []
top_latency = elapsed(result.get("agent_execution"))
if top_latency is not None:
    latencies.append(top_latency)
else:
    latencies.extend(value for value in (
        elapsed(step.get("agent_execution")) for step in result.get("step_results") or []
    ) if value is not None)

prompt = total("n_input_tokens")
completion = total("n_output_tokens")

# Harbor agents call the provider directly, so their spend is priced here or
# nowhere. Harbor reports a cost of its own when its LiteLLM knows the model;
# treat a reported 0.0 as "could not price" rather than "free" - a run that
# consumed tokens did not cost nothing - and fall back to pricing the tokens.
harbor_reported = total("cost_usd")
cost = harbor_reported if harbor_reported else None
if cost is None and (prompt or completion):
    try:
        import pricing
        cost = pricing.cost_usd(os.environ.get("LLM_MODEL", ""), prompt or 0,
                                completion or 0, os.environ.get("LLM_PROVIDER", ""),
                                cached_tokens=total("n_cache_tokens") or 0)
    except Exception:
        cost = None

usage = {
    "calls": None,
    "prompt_tokens": prompt,
    "completion_tokens": completion,
    "cache_tokens": total("n_cache_tokens"),
    "total_tokens": prompt + completion if prompt is not None and completion is not None else None,
    "cost_usd": cost,
    "latency_s": round(sum(latencies), 3) if latencies else None,
    "source": "harbor_result",
}
Path(sys.argv[2]).write_text(json.dumps(usage, indent=2) + "\n", encoding="utf-8")
exception = result.get("exception_info") if isinstance(result.get("exception_info"), dict) else None
diagnostics = {
  "trial_name": result.get("trial_name"),
  "exception": ({key: exception.get(key) for key in
           ("exception_type", "exception_message", "occurred_at")} if exception else None),
  "has_agent_result": isinstance(result.get("agent_result"), dict),
  "step_count": len(result.get("step_results") or []),
  "agent_execution": result.get("agent_execution"),
  "finished_at": result.get("finished_at"),
}
Path(sys.argv[3]).write_text(json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8")
PY
  fi
  return 0
}

# --- recovery helpers (copy agent-written artifacts out of the trial) --------
# An app writes its result to $ADHERENCE_OUTPUT_DIR, and the two conventions in
# use put it in different places under the trial's artifacts/ tree:
#
#   /app/output      -> artifacts/app/output/<name>
#   /logs/artifacts  -> artifacts/logs/artifacts/<name>   (harbor's own convention)
#
# Most start scripts moved to /logs/artifacts because it is a host bind-mount
# collected with no container ops, while /app/output needs `docker compose cp`,
# which hangs on a busy pid:host CUA container. Searching only the first path
# made every one of those tasks report "agent produced no <file>" and exit 1 —
# recorded as `error` even when the agent had done the task and the verifier had
# already scored it 1.0. Look in both, in the order a task is most likely to use.
_HARBOR_ARTIFACT_ROOTS="artifacts/app/output artifacts/logs/artifacts"

# harbor_recover_file <path-under-an-artifact-root> <dest-basename>
harbor_recover_file() {
  local dest="$OUTPUT_DIR/$2" root src
  if [ -n "${_TRIAL:-}" ]; then
    for root in $_HARBOR_ARTIFACT_ROOTS; do
      src="$_TRIAL/$root/$1"
      if [ -s "$src" ]; then
        cp "$src" "$dest"
        return 0
      fi
    done
  fi
  # The agent finished without writing what the verifier reads. Pack the
  # trajectory first so trace.zip survives before exiting.
  harbor_pack_trace
  echo "solve: agent produced no '$1' — agent=$AGENT provider=$PROVIDER model=$MODEL" >&2
  if [ "${ADHERENCE_OPTIONAL_ARTIFACTS:-0}" = "1" ]; then
    return 0
  fi
  exit 1
}
# harbor_recover_dir <dir-under-an-artifact-root> <dest-dir-basename>
harbor_recover_dir() {
  local dest="$OUTPUT_DIR/$2" root src
  if [ -n "${_TRIAL:-}" ]; then
    for root in $_HARBOR_ARTIFACT_ROOTS; do
      src="$_TRIAL/$root/$1"
      if [ -d "$src" ]; then
        mkdir -p "$dest"; cp "$src"/* "$dest"/ 2>/dev/null || true
        return 0
      fi
    done
  fi
  return 0
}
# harbor_pack_trace — zip the agent trajectory (+ screenshots) into trace.zip
harbor_pack_trace() {
  [ -n "${_TRIAL:-}" ] || return 0
  echo "$_TRIAL" > "$OUTPUT_DIR/harbor_trial.txt"
  ( cd "$_TRIAL/agent" 2>/dev/null &&
      zip -q -r "$OUTPUT_DIR/trace.zip" screenshot_*.webp trajectory.json final_answer.txt 2>/dev/null ) || true
}
