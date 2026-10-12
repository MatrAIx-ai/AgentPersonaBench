#!/usr/bin/env python3
"""Run one adherence task end-to-end and write a trial envelope to results/.

Pipeline per task:
    1. run solution/solve.sh  (generates the anchor + contrast arms)
    2. run tests/verifier.py (rule-based / llm-judge verifier -> reward + findings)
    3. write a trial envelope to
       evaluation/results/<task-path>/<model>/<effort>/<timestamp>.json

The result directory mirrors tasks/ exactly, then adds <model>/<effort>.

Usage:
    python evaluation/run_task.py <task-path> [--model opus-4-8] [--effort medium] [--seed 0]

    <task-path> is relative to tasks/, e.g.
        health-lifestyle/diet-type/vegan/app/task-001
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
# Tasks live under one of these roots (single- vs multi-attribute). A <task-path>
# is given WITHOUT the root prefix; the runner resolves it against each root so
# result paths (RESULTS / task) stay stable regardless of which bucket holds it.
TASK_ROOTS = [
    REPO / "tasks" / "single-attribute",
    REPO / "tasks" / "multi-attribute",
]
RESULTS = REPO / "evaluation" / "results"
CONFIGS = REPO / "evaluation" / "configs"


# The universal top-level keys every trial's structured_output shares. Anything
# a verifier emits OUTSIDE this set is task-specific and gets folded into the
# criterion's `raw` bag (mirrors 8B's Score.raw), so the generic contract and
# task-specific data never mix at the top level.
_UNIVERSAL_KEYS = {"reward", "score", "detail", "kind", "passed", "persona",
                   "criteria", "checks", "verdict", "passed_count", "total_checks",
                   "points", "max_points"}


def _normalize_output(findings: dict, evaluator: str | None) -> dict:
    """Align a verifier's structured_output.json to the shared 8B-style Reward
    contract, without touching the per-task verifiers. Produces:
      - score : the numeric result (mirrors reward)
      - kind  : how it was judged — "programmatic" | "llm" (from task evaluator)
      - criteria : one entry per checked sub-condition, each with a `raw` bag
        holding that task's own data. Multi tasks already emit `checks` (surfaced
        as criteria); single tasks get one synthesized criterion whose `raw`
        collects every task-specific field (e.g. animal_in_cart, anchor_terms).
    Idempotent: re-running leaves an already-normalized dict unchanged."""
    out = dict(findings)
    out.setdefault("score", out.get("reward"))
    out.setdefault("kind", "llm" if (evaluator or "").startswith("llm") else "programmatic")
    if "criteria" not in out:
        if isinstance(out.get("checks"), list):
            out["criteria"] = out["checks"]
        else:
            # everything the verifier emitted beyond the universal keys is
            # task-specific -> move it into raw and drop it from the top level,
            # keeping the generic contract and task data cleanly separated.
            task_keys = [k for k in out if k not in _UNIVERSAL_KEYS]
            raw = {k: out.pop(k) for k in task_keys}
            out["criteria"] = [{
                "name": out.get("dimension_id") or "adherence",
                "value": float(out.get("reward", 0.0) or 0.0),
                "verdict": out.get("verdict") or ("HELD" if out.get("passed") else "VIOLATED"),
                "passed": bool(out.get("passed", (out.get("reward", 0) or 0) >= 1.0)),
                "raw": raw,
            }]
    return out


# Verifiers that catch a judge or configuration failure write a normal-looking
# result -- reward 0, `verdict: "ERROR"` -- with no top-level `error` key. Read
# naively that is a scored 0: an outage or a malformed judge reply becomes a
# model failure. These are the shapes they use to say "I could not score this".
_VERIFIER_ERROR_STATUSES = {"judge_error", "configuration_error"}


def _verifier_reported_error(findings: dict) -> str | None:
    """Why the verifier could not score the trial, or None if it scored it."""
    if findings.get("error"):
        return str(findings["error"])
    if findings.get("status") in _VERIFIER_ERROR_STATUSES:
        return f"verifier status {findings['status']}: {findings.get('detail', '')}".strip()
    if findings.get("error_stage"):
        return f"verifier error at {findings['error_stage']}: {findings.get('detail', '')}".strip()
    if str(findings.get("verdict", "")).upper() == "ERROR":
        return f"verifier verdict ERROR: {findings.get('detail', '')}".strip()
    for check in findings.get("checks") or []:
        if isinstance(check, dict) and str(check.get("verdict", "")).upper() == "ERROR":
            return f"check {check.get('dimension_id') or check.get('name') or '?'} verdict ERROR"
    return None


def _normalize_trajectory(gen: dict) -> dict:
    """Unify a generation.json into an ATIF-lite trajectory so chat / web / app
    share one shape (mirrors 8B's ATIF trajectory.json). chat solvers emit
    `full_transcript`; web/app emit `trajectory`. We surface both as `steps` with
    a `schema_version`, leaving the original fields untouched for provenance."""
    if not isinstance(gen, dict) or "steps" in gen:
        return gen
    out = dict(gen)
    src = gen.get("trajectory") or gen.get("full_transcript") or []
    steps = []
    for i, s in enumerate(src):
        if isinstance(s, dict) and ("role" in s or "content" in s):  # chat message
            steps.append({"step_id": i + 1, "source": s.get("role", "agent"),
                          "message": s.get("content", ""), "raw": s})
        else:  # web/app action step
            steps.append({"step_id": i + 1, "source": "agent",
                          "action": (s.get("step") if isinstance(s, dict) else str(s)),
                          "raw": s})
    if steps:
        out["schema_version"] = "ATIF-lite-v1"
        out["steps"] = steps
    return out


def _load_arm_config(arm: str) -> dict:
    """Load configs/<arm>.json — the single source of truth for a model arm's
    settings (model id, gateway, endpoint, temperature, token env). An unknown arm
    (no config file) is a hard error: every arm must have a config."""
    path = CONFIGS / f"{arm}.json"
    if not path.is_file():
        known = ", ".join(sorted(p.stem for p in CONFIGS.glob("*.json"))) or "(none)"
        raise SystemExit(
            f"error: no config for arm '{arm}' at {path.relative_to(REPO)}. "
            f"Known arms: {known}. Add a configs/<arm>.json for it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_task_dir(task: str):
    """Return (task_dir, root_name) so results mirror single-/multi- bucket."""
    for root in TASK_ROOTS:
        d = root / task
        if (d / "task.toml").is_file():
            return d, root.name
    return None, None


def _load_task_meta(task_dir: Path) -> dict:
    with open(task_dir / "task.toml", "rb") as f:
        return tomllib.load(f)


def _check_pin(chk: dict) -> dict:
    """Normalize one check into the fields the envelope pins. Multi-attribute
    checks store the tested value under `value`; older single-attribute tasks use
    `anchor_value`. Fall back so `anchor_value` is never spuriously null when a
    value exists under the other key."""
    value = chk.get("value")
    anchor = chk.get("anchor_value")
    return {
        "dimension_id": chk.get("dimension_id"),
        "anchor_value": anchor if anchor is not None else value,
        "value": value if value is not None else anchor,
        "contrast_value": chk.get("contrast_value"),
        "evaluator": chk.get("evaluator"),
    }


def _persona_provenance(task_dir: Path) -> dict:
    """Snapshot the persona so a trial is self-describing: which persona ran and a
    content hash, so a later edit to persona.yaml is detectable from the trial
    alone (the contract's provenance requirement). Best-effort — a missing or
    unparseable persona yields nulls rather than aborting the run."""
    path = task_dir / "persona.yaml"
    out = {"persona_id": None, "source": None, "persona_sha256": None}
    if not path.is_file():
        return out
    raw = path.read_bytes()
    out["persona_sha256"] = hashlib.sha256(raw).hexdigest()
    try:
        import yaml  # optional dep; hash still recorded without it
        data = yaml.safe_load(raw.decode("utf-8")) or {}
        if isinstance(data, dict):
            out["persona_id"] = data.get("persona_id") or data.get("id")
            out["source"] = data.get("source")
    except Exception:  # noqa: BLE001 - provenance is best-effort
        pass
    return out


class _Timeout(Exception):
    """A solve/verify step exceeded its task.toml budget."""

    def __init__(self, stage: str, secs: float, stderr: str = "") -> None:
        super().__init__(f"{stage} exceeded {secs:.0f}s")
        self.stage, self.secs, self.stderr = stage, secs, stderr


def _run(cmd: list[str], env: dict, cwd: Path, *, timeout: float | None = None,
         stage: str = "step") -> subprocess.CompletedProcess:
    """Run a subprocess with an optional hard wall-clock budget.

    The child is started in its own process group so that on timeout we kill the
    WHOLE tree (bash wrapper + harbor + docker client it spawned), not just the
    immediate child — otherwise a hung agent/verifier keeps holding containers and
    API spend after we've given up. On expiry we raise _Timeout; the caller's
    finally-block still tears down the proxies.
    """
    if not timeout or timeout <= 0:
        return subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)
    proc = subprocess.Popen(cmd, env=env, cwd=cwd, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            start_new_session=True)  # own process group
    try:
        out, err = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, out, err)
    except subprocess.TimeoutExpired:
        # SIGTERM the group, give it a moment, then SIGKILL any survivors.
        import signal
        import time
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except ProcessLookupError:
                break
            try:
                proc.communicate(timeout=5)
                break
            except subprocess.TimeoutExpired:
                time.sleep(0.5)
        _, err = (proc.stdout, proc.stderr)
        raise _Timeout(stage, float(timeout))



def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("task", help="task path relative to tasks/")
    ap.add_argument("--model", default="opus-4-8", help="model arm id (results subdir)")
    ap.add_argument("--effort", default="medium", help="reasoning effort (results subdir)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--timestamp", default=None, help="ISO-8601 override (else now)")
    ap.add_argument("--suite-id", default=None, help="batch/suite identifier recorded in envelope.json")
    ap.add_argument("--run-key", default=None, help="unique batch run key recorded in envelope.json")
    ap.add_argument("--model-id", default=None, help="override the provider model id while retaining the arm config")
    args = ap.parse_args()
    run_started = datetime.now(timezone.utc)
    run_started_monotonic = time.monotonic()

    task_dir, root_name = _resolve_task_dir(args.task)
    if task_dir is None:
        roots = ", ".join(str(r.relative_to(REPO)) for r in TASK_ROOTS)
        print(f"error: no task.toml for '{args.task}' under {roots}", file=sys.stderr)
        sys.exit(2)

    meta = _load_task_meta(task_dir)
    # Every task pins its attribute(s) in [[checks]] (a single-attribute task is
    # just one check). Envelope-level fields come from the first check; the older
    # [adherence] table is still accepted as a fallback for un-migrated tasks.
    checks = meta.get("checks") or []
    # Envelope-level scalar fields still come from the first check for back-compat
    # (single-attribute tasks have exactly one), but the FULL per-check pin is
    # recorded under `checks` below so multi-attribute tasks aren't reduced to
    # their first attribute. The older [adherence] table is a fallback.
    adh = checks[0] if checks else meta.get("adherence", {})
    checks_pin = [_check_pin(c) for c in checks] if checks else (
        [_check_pin(meta.get("adherence", {}))] if meta.get("adherence") else [])
    persona_pin = _persona_provenance(task_dir)
    ts = args.timestamp or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # All arm/model settings come from configs/<arm>.json — never hardcoded here.
    cfg = _load_arm_config(args.model)
    provider = str(cfg.get("provider", "anthropic"))
    model_id = args.model_id or cfg["model"]

    # One clean directory per run, named trial-NNN (incrementing). The wall-clock
    # time is kept inside the envelope's `timestamp` field. Results mirror the
    # task's bucket (single-attribute / multi-attribute).
    effort_dir = RESULTS / root_name / args.task / args.model / args.effort
    effort_dir.mkdir(parents=True, exist_ok=True)
    existing = [p.name for p in effort_dir.glob("trial-*") if p.is_dir()]
    next_n = 1 + max([int(n.split("-")[1]) for n in existing if n.split("-")[1].isdigit()], default=0)
    run_dir = effort_dir / f"trial-{next_n:03d}"
    run_dir.mkdir(parents=True, exist_ok=True)

    env = dict(os.environ)
    env["ADHERENCE_OUTPUT_DIR"] = str(run_dir)
    env["ADHERENCE_SEED"] = str(args.seed)
    env["ADHERENCE_ARM"] = args.model   # arm id (e.g. opus-4-8) — app solve.sh maps it
    env["ADHERENCE_EFFORT"] = args.effort
    # Some models reject a reasoning_effort parameter outright; an arm declares
    # that once in its config rather than every task working around it.
    if cfg.get("forward_reasoning_effort") is False:
        env["ADHERENCE_FORWARD_EFFORT"] = "0"
    # The arm's sampling temperature has to reach the harbor agents too, or the
    # app surface silently runs at computer-1's own default (0.7) while the other
    # three use what the arm config declares — the same model, sampled two
    # different ways, in one score.
    if cfg.get("temperature") is not None:
        env["ADHERENCE_TEMPERATURE"] = str(cfg["temperature"])
    env["RUNTIME_PYTHON"] = sys.executable or "python3"

    # All four environments share ONE entry point: run solve.sh, then verifier.py.
    # app tasks are no different — their (self-contained) solve.sh runs the harbor
    # persona-computer-1 agent and drops the app-written output into
    # ADHERENCE_OUTPUT_DIR for the task's own verifier.py. No special-case branch.
    if True:
        # Provider-neutral LLM settings from the arm config. solvers call the shared
        # provider layer (llm_client on host, agent_client in containers) — never a
        # hardcoded vendor. LLM_PROVIDER selects the backend; LLM_MODEL the model id.
        env["LLM_PROVIDER"] = provider
        env["LLM_MODEL"] = model_id
        env["LLM_REASONING_EFFORT"] = args.effort
        env["LLM_CALL_ROLE"] = "arm"
        # An OpenAI-compatible arm (Qwen/DashScope, GLM/Z.ai, OpenRouter, a local
        # gateway) may pin its endpoint in the arm config. Exported per role so the
        # arm and the judge can sit on different endpoints; openai_compat resolves
        # the provider default when this is unset.
        base_url = str(cfg.get("base_url") or "").strip()
        if base_url:
            env["LLM_BASE_URL"] = base_url
        # The llm-judge is fixed by the BENCHMARK, not by the arm under test: every
        # arm must be scored by the same judge or the scores are not comparable.
        # The default lives in configs/judge.json; see evaluation/src/judge.py for
        # the override chain. Resolved here and exported so the verifier, which
        # runs in its own process, sees exactly what preflight checked.
        sys.path.insert(0, str(REPO / "evaluation" / "src"))
        import judge as _judge  # noqa: E402  (path set just above)

        resolved_judge = _judge.resolve(cfg, os.environ)
        judge_model = resolved_judge.model
        judge_provider = resolved_judge.provider
        judge_base_url = resolved_judge.base_url
        env["ADHERENCE_JUDGE_MODEL"] = judge_model
        env["ADHERENCE_JUDGE_PROVIDER"] = judge_provider
        if judge_base_url:
            env["ADHERENCE_JUDGE_BASE_URL"] = judge_base_url

        # Start the host-side LLM proxy so containerized (web/app) solvers can reach
        # the provider layer without any SDK or key of their own. Its URL is exported
        # for agent_client; the container reaches it via `docker run --network=host`.
        # The proxy runs in THIS process, so it resolves the provider from os.environ
        # — set it here too (not just in the child `env`), or the proxy falls back to
        # inferring the vendor from the model name.
        os.environ["LLM_PROVIDER"] = provider
        os.environ["LLM_MODEL"] = model_id
        os.environ["LLM_REASONING_EFFORT"] = args.effort
        os.environ["LLM_CALL_ROLE"] = "arm"
        os.environ["ADHERENCE_JUDGE_MODEL"] = judge_model
        os.environ["ADHERENCE_JUDGE_PROVIDER"] = judge_provider
        if base_url:
            os.environ["LLM_BASE_URL"] = base_url
        if judge_base_url:
            os.environ["ADHERENCE_JUDGE_BASE_URL"] = judge_base_url
        sys.path.insert(0, str(REPO / "evaluation" / "src"))
        from llm_proxy import LLMProxy  # noqa: E402  (path set just above)

        proxy = LLMProxy().start()
        # Docker Desktop does not share the macOS host's loopback namespace with
        # Linux containers. Its stable host alias forwards back to the loopback-
        # bound proxy; native Linux `--network=host` can use 127.0.0.1 directly.
        env["LLM_PROXY_URL"] = (
            f"http://host.docker.internal:{proxy.port}"
            if sys.platform == "darwin"
            else proxy.url
        )

        def _stop_services() -> None:
            proxy.stop()

        # Wrap the whole solve+verify block in try/finally so the background HTTP
        # LLMProxy is ALWAYS torn down — even if solve.sh
        # invocation, the verifier subprocess, or a JSON/OS error raises. Without
        # this, an exception between proxy start and the explicit stop leaks both
        # server threads and their bound ports.
        #
        # Initialize outcomes BEFORE the try so the post-finally status block never
        # dereferences an undefined name. If `_run(["bash", ...])` itself raises (e.g.
        # bash missing -> OSError), `finally` still tears down services and the raised
        # exception propagates — but `solve` stays None, so the guarded block below is
        # skipped and the real error isn't masked by a NameError on `solve.returncode`.
        # Wall-clock budgets from task.toml. The agent step is the whole solve.sh
        # wrapper (which itself runs `harbor run`); harbor may bound the agent
        # internally, but the top-level wrapper and the verifier subprocess are
        # otherwise unbounded — a hang there holds the terminal, containers, and API
        # spend forever. `solve` gets the agent budget plus a small margin for the
        # wrapper's own setup/recovery; verify gets the verifier budget. 0/absent
        # disables the limit for that step.
        agent_budget = float((meta.get("agent") or {}).get("timeout_sec") or 0) or None
        verifier_budget = float((meta.get("verifier") or {}).get("timeout_sec") or 0) or None
        solve_budget = (agent_budget + 120) if agent_budget else None  # + wrapper margin

        solve = None
        status, reward, findings = "error", 0.0, {}
        model_usage: dict = {}
        model_calls: list = []
        harbor_usage: dict = {}
        chat_usage: dict = {}
        harbor_diagnostics: dict = {}
        solve_duration_s = 0.0
        verifier_duration_s = 0.0
        try:
            # 1. solve (generates arms). 2. verify (writes reward.txt + structured_output.json).
            stage_started = time.monotonic()
            solve = _run(["bash", str(task_dir / "solution" / "solve.sh")], env, REPO,
                         timeout=solve_budget, stage="solve")
            solve_duration_s = time.monotonic() - stage_started
            harbor_usage_path = run_dir / "harbor_usage.json"
            if harbor_usage_path.is_file():
                try:
                    loaded_usage = json.loads(harbor_usage_path.read_text(encoding="utf-8"))
                    if isinstance(loaded_usage, dict):
                        harbor_usage = loaded_usage
                except (OSError, json.JSONDecodeError):
                    pass
            chat_usage_path = run_dir / "chat_usage.json"
            if chat_usage_path.is_file():
                try:
                    loaded_chat = json.loads(chat_usage_path.read_text(encoding="utf-8"))
                    if isinstance(loaded_chat, dict):
                        chat_usage = loaded_chat
                except (OSError, json.JSONDecodeError):
                    pass
            harbor_diagnostics_path = run_dir / "harbor_diagnostics.json"
            if harbor_diagnostics_path.is_file():
                try:
                    loaded_diagnostics = json.loads(harbor_diagnostics_path.read_text(encoding="utf-8"))
                    if isinstance(loaded_diagnostics, dict):
                        harbor_diagnostics = loaded_diagnostics
                except (OSError, json.JSONDecodeError):
                    pass
            if solve.returncode != 0:
                status, reward, findings = "error", 0.0, {"stage": "solve", "stderr": solve.stderr[-800:]}
            else:
                # Run the verifier with an interpreter that carries the runtime
                # deps, NOT bare `python3`: chat verifiers import llm_client ->
                # anthropic, and a bare system python3 lacks it, so `verify` died
                # with ModuleNotFoundError even though `solve` produced a good
                # artifact. Prefer $RUNTIME_PYTHON, else the interpreter running
                # this runner (which necessarily has the deps run_task itself uses).
                verifier_py = os.environ.get("RUNTIME_PYTHON") or sys.executable or "python3"
                verifier_env = dict(env)
                verifier_env["LLM_CALL_ROLE"] = "judge"
                stage_started = time.monotonic()
                verify = _run([verifier_py, str(task_dir / "tests" / "verifier.py")], verifier_env, REPO,
                              timeout=verifier_budget, stage="verify")
                verifier_duration_s = time.monotonic() - stage_started
                so = run_dir / "structured_output.json"
                try:
                    if not so.is_file():
                        raise ValueError(f"verifier wrote no structured_output.json; stderr: {verify.stderr[-400:]}")
                    findings = _normalize_output(json.loads(so.read_text()), adh.get("evaluator"))
                    so.write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
                    # unify the trajectory to ATIF-lite. generation.json may be root-owned
                    # (docker-written) so we write the normalized copy to trajectory.json
                    # rather than mutating it in place.
                    gen = run_dir / "generation.json"
                    if gen.is_file():
                        atif = _normalize_trajectory(json.loads(gen.read_text()))
                        if "steps" in atif:
                            (run_dir / "trajectory.json").write_text(
                                json.dumps({"schema_version": atif["schema_version"],
                                            "steps": atif["steps"]}, ensure_ascii=False, indent=2),
                                encoding="utf-8")
                except (ValueError, json.JSONDecodeError, OSError) as e:
                    # a broken/missing verifier output is an error, not a silent pass
                    findings = {"stage": "verify", "error": str(e), "stderr": verify.stderr[-400:]}
                # A verifier that writes structured_output.json but omits the 'reward'
                # key is broken — scoring it 0.0 would be a false fail that hides the
                # bug. Treat an ABSENT reward key (with no error already recorded) as a
                # verifier error. A present reward:0.0 stays a legit fail.
                if "reward" not in findings and "error" not in findings:
                    findings = {"stage": "verify",
                                "error": "verifier wrote structured_output.json with no 'reward' key"}
                reward = float(findings.get("reward", 0.0))
        except _Timeout as to:
            # A step blew its budget; the process group has been killed. Record it
            # as a distinct terminal outcome (not a silent 0.0 fail) so batch runs
            # can see the trial timed out rather than legitimately failing.
            timed_out = True
            status, reward, findings = "timeout", 0.0, {
                "stage": to.stage, "error": str(to), "timeout_sec": to.secs}
            elapsed = time.monotonic() - stage_started
            if to.stage == "solve":
                solve_duration_s = elapsed
            else:
                verifier_duration_s = elapsed
        except Exception as exc:  # noqa: BLE001 - batch runs must retain an envelope
            timed_out = False
            status, reward, findings = "error", 0.0, {
                "stage": "solve" if solve is None else "verify",
                "error": f"{type(exc).__name__}: {exc}",
            }
        else:
            timed_out = False
        finally:
            model_usage = proxy.summary()
            model_calls = proxy.calls()
            if chat_usage:
                # A chat trial runs its model calls in a subprocess, so the host
                # proxy counts none of them. Its own record is the only account.
                proxy_tokens = model_usage.get("total_tokens") or 0
                if proxy_tokens == 0:
                    model_usage = chat_usage
            if harbor_usage:
                # Harbor-native agents call the provider directly, so proxy totals
                # are normally zero. Prefer Harbor's persisted aggregate in that
                # case; preserve proxy accounting for non-Harbor task surfaces.
                proxy_tokens = model_usage.get("total_tokens") or 0
                if proxy_tokens == 0:
                    model_usage = harbor_usage
            elif model_usage.get("calls") == 0:
                # Zero proxy calls means "not measured", not a zero-token model run.
                model_usage = {}
            _stop_services()
        if not timed_out and solve is not None and solve.returncode == 0:
            verifier_error = _verifier_reported_error(findings)
            if verifier_error is not None:
                status = "error"
                findings.setdefault("error", verifier_error)
            else:
                # pass iff every criterion held: score == max_points (multi is 0..N),
                # or reward >= 1.0 for single tasks that report no max_points.
                max_pts = findings.get("max_points")
                status = "pass" if (reward >= max_pts if isinstance(max_pts, (int, float)) and max_pts
                                    else reward >= 1.0) else "fail"
        if status in {"error", "timeout"} and harbor_diagnostics:
            findings["harbor_diagnostics"] = harbor_diagnostics

    # Primary human-facing score. multi tasks report an integer points/max_points
    # (e.g. "1/3" — one style check held of three); single tasks are binary, shown
    # as "1/1" (held) or "0/1" (violated). This is the authoritative "final score";
    # `reward` below stays as the raw numeric the verifier emitted.
    pts = findings.get("points")
    max_pts = findings.get("max_points")
    if isinstance(pts, (int, float)) and isinstance(max_pts, (int, float)) and max_pts:
        score = f"{int(pts)}/{int(max_pts)}"
    else:
        score = f"{1 if reward >= 1.0 else 0}/1"

    envelope = {
        "suite_id": args.suite_id,
        "run_key": args.run_key,
        "task": args.task,
        "task_version": meta.get("version"),
        "score": score,
        # First-check scalars (back-compat). anchor_value falls back to `value`
        # so multi-attribute tasks — which store the tested value under `value` —
        # no longer pin a null here.
        "dimension_id": adh.get("dimension_id"),
        "anchor_value": adh.get("anchor_value") if adh.get("anchor_value") is not None
                        else adh.get("value"),
        "contrast_value": adh.get("contrast_value"),
        "evaluator": adh.get("evaluator"),
        # Full per-check pin — every attribute tested, its value and evaluator, so
        # a multi-attribute trial is not reduced to just its first check.
        "checks": checks_pin,
        # Persona provenance: which persona ran + a content hash, so a later edit
        # to persona.yaml is detectable from the trial alone.
        "persona_id": persona_pin["persona_id"],
        "source": persona_pin["source"],
        "persona_sha256": persona_pin["persona_sha256"],
        "arm": args.model,
        "model": model_id,
        # resolved arm config — pins the exact call settings for reproducibility
        "provider": cfg.get("provider"),
        "endpoint": cfg.get("endpoint"),
        "temperature": cfg.get("temperature"),
        "max_tokens": cfg.get("max_tokens"),
        "effort": args.effort,
        "judge_model": judge_model,
        "judge_provider": judge_provider,
        "seed": args.seed,
        "timestamp": ts,
        "started_at": run_started.isoformat().replace("+00:00", "Z"),
        "finished_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "timing": {
            "total_s": round(time.monotonic() - run_started_monotonic, 3),
            "solve_s": round(solve_duration_s, 3),
            "verify_s": round(verifier_duration_s, 3),
        },
        "model_usage": model_usage,
        "model_calls": model_calls,
        "status": status,
        "reward": reward,
        "findings": findings,
    }

    env_path = run_dir / "envelope.json"
    env_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{status.upper():5s} {args.model:14s} score={score} -> {env_path.relative_to(REPO)}")

    # Exit code so batch scripts / CI can detect failures:
    #   0 = pass | 1 = fail (ran, verdict VIOLATED) | 3 = error (crash/broken output)
    #   | 124 = timeout (a step exceeded its task.toml budget; matches GNU timeout(1))
    # The envelope is always written first, so an error/timeout trial stays auditable.
    if status == "timeout":
        sys.exit(124)
    if status == "error":
        sys.exit(3)
    if status == "fail":
        sys.exit(1)


if __name__ == "__main__":
    main()
