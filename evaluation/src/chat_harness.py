"""Chat env harness — drive a persona through a multi-turn chat as a real AGENT.

The persona is played by harbor's UserSimulator (an agent that decides each turn),
talking to a bot the *task* defines with a single prompt. No HTTP sidecar / compose:
the bot is a local ChatSessionPort that calls an LLM with the task's bot prompt.
Complexity lives here in the infra; each chat task stays minimal — a persona.yaml,
a bot prompt, an instruction, and a verifier that judges the transcript.

Usage from a task's solve.sh:
    python3 -c "from chat_harness import run_chat_adherence; \
        run_chat_adherence(task_dir, out_dir, arm)"
It writes transcript.json (+ user_turns.json for the adherence verifier).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import usage
from llm_client import chat

REPO_SRC = Path(__file__).resolve().parent


# --- the bot: a ChatSessionPort backed by one prompt + an LLM ----------------
class PromptBotSession:
    """A chat 'SUT' defined entirely by a system prompt. Implements the
    ChatSessionPort the UserSimulator drives: each run_turn_sync appends the user
    message, calls the LLM with the bot's persona (system prompt), returns its
    reply. This replaces harbor's HTTP chatbot sidecar with a local, task-defined
    bot — so a chat task needs no compose/sidecar, just a prompt."""

    def __init__(self, system_prompt: str, model: str, *, temperature: float = 0.6,
                 role: str | None = None):
        self._system = system_prompt
        self._model = model
        self._role = role
        self._temp = temperature
        self._history: List[Dict[str, str]] = []
        self.session_id = "prompt-bot"

    def run_turn_sync(self, message: str) -> Dict[str, Any]:
        self._history.append({"role": "user", "content": message})
        routing = {"call_role": self._role} if self._role else {}
        reply = chat(
            [{"role": "system", "content": self._system}, *self._history],
            model=self._model,
            max_tokens=1024,
            temperature=self._temp,
            **routing,
        )
        self._history.append({"role": "assistant", "content": reply})
        return {"assistantMessage": reply, "items": []}

# The model comes from LLM_MODEL, exported by run_task.py from configs/<arm>.json
# — the single source of truth. A hardcoded arm->model map used to live here and
# silently ran every arm as claude-sonnet-4.6 while the envelope recorded the
# config model, mislabeling every chat trial. No fallback: a missing LLM_MODEL is
# a wiring error we want to surface loudly, not paper over with a default.


# The bot the persona talks to is played by the arm's own model by default, as
# in every run so far. APB_CHAT_BOT_MODEL=<model> fixes it to one model for all
# arms instead (e.g. gpt-5.6-luna: every arm then meets the same pressure, and a
# terse arm cannot play a blank bot). A fixed bot is routed like the judge when
# it is the judge's model (same key and endpoint), else by its own name.
DEFAULT_CHAT_BOT_MODEL = "arm"


def _bot_model(arm_model: str) -> tuple:
    bot = (os.environ.get("APB_CHAT_BOT_MODEL") or DEFAULT_CHAT_BOT_MODEL).strip()
    if bot.lower() == "arm":
        return arm_model, {}
    judge = (os.environ.get("ADHERENCE_JUDGE_MODEL") or "").strip()
    return bot, {"role": "judge" if judge and bot.lower() == judge.lower() else "bot"}


def _run_chat(task_dir: str, out_dir: str, arm: str, *, max_turns: int):
    """Shared core: run the persona (UserSimulator agent) against the task's
    prompt-defined bot for a fixed number of turns. Writes transcript.json +
    user_turns.json and returns (persona, list_of_PlaygroundTurn, out_path)."""
    import sys
    sys.path.insert(0, str(REPO_SRC))
    from matraix.agents.persona.loader import load_persona
    from playground.types import PlaygroundConfig
    from playground.user_sim.runner import run_playground

    task = Path(task_dir)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise SystemExit(
            f"chat_harness: LLM_MODEL is unset for arm '{arm}' — run_task.py must "
            "export it from configs/<arm>.json (no hardcoded fallback)")

    persona = load_persona(str(task / "persona.yaml"))
    bot_prompt = (task / "input" / "bot.md").read_text(encoding="utf-8")
    sut_desc = (task / "input" / "context.md").read_text(encoding="utf-8") \
        if (task / "input" / "context.md").is_file() else "a chat assistant"

    # The sim's frame (instruction.md + input/context.md) comes from the task
    # bundle, which the runner loads from a repo-relative task_path. Locate the
    # benchmark repo root (the dir holding tasks/) and express task_path relative
    # to it, so the sim knows what application it's talking to — that context, plus
    # the persona's own attributes, is what drives latent adherence.
    repo_root = task.resolve()
    while repo_root != repo_root.parent and not (repo_root / "tasks").is_dir():
        repo_root = repo_root.parent
    try:
        rel_task_path = str(task.resolve().relative_to(repo_root))
    except ValueError:
        rel_task_path = None

    # Which application the sim is told it's talking to. PlaygroundConfig defaults
    # application_id to "meal_planning_nutrition", which mislabels every non-meal
    # chat task (a SIM-activation or finance persona was told it was chatting with
    # "Meal Planning Nutrition" and noticed). Read an optional per-task override
    # from task.toml [metadata].application_id; otherwise use a neutral generic so
    # no task inherits the meal default. The real scenario still reaches the sim via
    # context.md (sut_desc) — this only fixes the chatbot's displayed name.
    application_id = "assistant"
    task_toml = task / "task.toml"
    if task_toml.is_file():
        try:
            import tomllib
            meta = tomllib.loads(task_toml.read_text(encoding="utf-8"))
            application_id = ((meta.get("metadata") or {}).get("application_id")
                              or application_id)
        except Exception:  # noqa: BLE001 - a bad toml shouldn't block the run
            pass

    # force_full_turns: keep the bot applying pressure for the whole run so the
    # persona's commitment is actually tested (the sim would otherwise stop once
    # its own goal felt met, after only a few turns).
    config = PlaygroundConfig(persona_model=model, max_turns=max_turns,
                              force_full_turns=True, application_id=application_id)
    bot_model, bot_kw = _bot_model(model)
    session = PromptBotSession(bot_prompt, bot_model, **bot_kw)
    result = run_playground(
        session, persona, sut_desc, config,
        created_at="1970-01-01T00:00:00Z",
        persona_yaml_path=str(task / "persona.yaml"),
        task_path=rel_task_path,
        repo_root=repo_root,
    )
    turns = list(result.transcript or [])
    # A PlaygroundTurn carries both sides; flatten to a role/content transcript.
    transcript: List[Dict[str, str]] = []
    for t in turns:
        transcript.append({"role": "user", "content": t.user_message})
        transcript.append({"role": "assistant", "content": t.assistant_message})
    (out / "transcript.json").write_text(
        json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    # user_turns.json: what the persona said (what the adherence judge reads).
    (out / "user_turns.json").write_text(
        json.dumps({"persona": persona.persona_id or "persona",
                    "turns": [t.user_message for t in turns]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    # trace.zip: contract-layer parity with the survey/web/app modalities. Chat is
    # an LLM-to-LLM prompt-bot run (no browser/desktop, so no screenshots) — its
    # native trace is the transcript + the persona's own turns. Package whatever
    # of the trial's JSON artifacts exist so downstream tooling finds a trace.zip
    # for every modality.
    # This runs in a subprocess of its own, so the host proxy in run_task sees no
    # calls and the trial would otherwise report zero tokens for the most
    # expensive surface. Hand the recorded spend out the same way harbor does.
    chat_usage = usage.summary()
    if chat_usage:
        # Who played which side: the persona is the arm; the bot is fixed.
        chat_usage["bot_model"] = bot_model
        by_model: dict = {}
        for c in usage.CALL_LOG:
            m = by_model.setdefault(str(c.get("model")), {"calls": 0, "prompt_tokens": 0, "completion_tokens": 0})
            m["calls"] += 1
            m["prompt_tokens"] += c.get("prompt_tokens") or 0
            m["completion_tokens"] += c.get("completion_tokens") or 0
        chat_usage["by_model"] = by_model
        (out / "chat_usage.json").write_text(
            json.dumps(chat_usage, indent=2) + "\n", encoding="utf-8")
    _write_chat_trace_zip(out)
    return persona, turns, out


def _write_chat_trace_zip(out: Path) -> None:
    """Bundle the chat trial's JSON artifacts into ``out/trace.zip``.

    Mirrors the per-modality ``trace.zip`` the harbor path emits (screenshots +
    trajectory for CUA/web). Chat has no screenshots; its trace is the dialogue.
    """
    import zipfile

    members = ["transcript.json", "user_turns.json", "generation.json",
               "trajectory.json"]
    zip_path = out / "trace.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in members:
            path = out / name
            if path.is_file():
                zf.write(path, arcname=name)


def run_chat_adherence(task_dir: str, out_dir: str, arm: str = "opus-4-8") -> None:
    """Chat trial where the verifier judges the persona's own turns (did it hold
    its trait under the bot's pressure). Writes transcript.json + user_turns.json."""
    _run_chat(task_dir, out_dir, arm, max_turns=12)


def _last_code_block(text: str) -> str | None:
    """Return the last complete, parseable Python module in an assistant reply, or
    None. Guards against chit-chat and replies truncated at max_tokens (which would
    otherwise overwrite the last good code)."""
    import ast
    import re

    body = text.strip()
    fenced = re.findall(r"```(?:python)?\s*(.*?)```", body, re.S)
    candidate = fenced[-1].strip() if fenced else body
    if not re.search(r"(^|\n)\s*(def |class |import |from )", candidate):
        return None
    try:
        ast.parse(candidate)
    except SyntaxError:
        return None
    return candidate


def run_chat_codegen(task_dir: str, out_dir: str, arm: str = "opus-4-8") -> None:
    """Chat trial where the persona drives a coding bot; we keep the LAST code the
    bot produced and write it to solution/solution.py for a rule-based style
    verifier. The persona's style preferences surface through what it asks for."""
    _persona, turns, out = _run_chat(task_dir, out_dir, arm, max_turns=4)
    last_code = None
    for t in turns:
        code = _last_code_block(t.assistant_message or "")
        if code:
            last_code = code
    if not last_code:
        raise RuntimeError("bot never produced parseable code across the conversation")
    sol = out / "solution"; sol.mkdir(parents=True, exist_ok=True)
    (sol / "solution.py").write_text(last_code + "\n", encoding="utf-8")
