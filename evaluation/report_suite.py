#!/usr/bin/env python3
"""Aggregate a PersonaBench suite into pilot leaderboard and task-health reports."""
from __future__ import annotations

import argparse
import csv
import html
import json
import sys
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
SUITES = REPO / "evaluation" / "results" / "suites"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def latest_events(path: Path) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "completed" and event.get("run_key"):
            result[str(event["run_key"])] = event
    return result


def usage_for(envelope_path: Path | None) -> dict[str, Any]:
    """The trial's token usage, from whichever record actually carries it.

    A web trial writes BOTH a `generation.json` and the envelope, and its
    generation.json reports `token_usage: {calls: 1, total_tokens: 0, ...}` —
    the shape is right, the counts are not, because the containerised solver
    counts its own calls while the tokens are known only to the host proxy that
    served them. Taking the first dict-shaped record meant that zero shadowed
    the envelope's real `model_usage` on 85 web trials, and the web column read
    as though almost nothing had been spent there.

    So: prefer a record with actual counts, and fall back to the first
    well-formed one only to keep `calls`/`latency_s` when nobody counted tokens.
    """
    if envelope_path is None:
        return {}
    generation = load_json(envelope_path.parent / "generation.json")
    envelope = load_json(envelope_path)
    candidates = [generation.get("token_usage"), generation.get("usage"),
                  envelope.get("model_usage")]
    dicts = [u for u in candidates if isinstance(u, dict)]
    for usage in dicts:
        if usage.get("total_tokens") or usage.get("prompt_tokens") or usage.get("completion_tokens"):
            return usage
    return dicts[0] if dicts else {}


def classify_error(event: dict[str, Any], envelope: dict[str, Any]) -> str:
    status = str(event.get("status", "missing"))
    if status not in {"error", "timeout", "preflight_error"}:
        return ""
    if status == "preflight_error":
        return "preflight"
    findings = envelope.get("findings") if isinstance(envelope.get("findings"), dict) else {}
    stage = str(findings.get("stage") or "runner")
    text = " ".join(str(value) for value in (
        findings.get("error"), findings.get("stderr"), event.get("stderr_tail"), event.get("stdout_tail")
    ) if value).lower()
    if any(token in text for token in ("api key", "authentication", "unauthorized", "401")):
        return "credential"
    if any(token in text for token in ("rate limit", "429", "overload", "529")):
        return "rate_limit"
    if "docker" in text or "container" in text or "image" in text:
        return "environment"
    if status == "timeout":
        return f"{stage}_timeout"
    return stage


def parse_score(score: Any) -> tuple[float, float] | None:
    """(points, max_points) from an "a/b" score string, or None."""
    if not isinstance(score, str) or "/" not in score:
        return None
    try:
        points, max_points = (float(part) for part in score.split("/", 1))
    except ValueError:
        return None
    return (points, max_points) if max_points > 0 else None


def build_rows(suite_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    plan = load_json(suite_dir / "plan.json")
    events = latest_events(suite_dir / "events.jsonl")
    rows: list[dict[str, Any]] = []
    for event in events.values():
        envelope_path = REPO / event["envelope"] if event.get("envelope") else None
        envelope = load_json(envelope_path) if envelope_path else {}
        findings = envelope.get("findings") if isinstance(envelope.get("findings"), dict) else {}
        score = envelope.get("score", event.get("score"))
        score_points = parse_score(score)
        max_points = findings.get("max_points")
        if not isinstance(max_points, (int, float)) or max_points <= 0:
            # No envelope here (moved, pruned, or never copied): the event's
            # "a/b" score still carries the denominator. Falling back to the
            # check count instead gave 1 for every multi-attribute task, so a
            # 3/3 was reported as a normalized reward of 3.0.
            max_points = score_points[1] if score_points else max(1, len(envelope.get("checks") or []))
        reward = envelope.get("reward", event.get("reward"))
        normalized = (float(reward) / float(max_points)) if isinstance(reward, (int, float)) else None
        timing = envelope.get("timing") if isinstance(envelope.get("timing"), dict) else {}
        usage = usage_for(envelope_path)
        rows.append({
            "run_key": event.get("run_key"), "bucket": event.get("bucket"), "task": event.get("task"),
            "surface": event.get("surface"), "model": event.get("model"), "effort": event.get("effort"),
            "seed": event.get("seed"), "status": event.get("status"), "score": score,
            "reward": reward, "max_points": max_points, "normalized_reward": normalized,
            "duration_s": timing.get("total_s", event.get("duration_s")), "solve_s": timing.get("solve_s"),
            "verify_s": timing.get("verify_s"), "model_latency_s": usage.get("latency_s"),
            "prompt_tokens": usage.get("prompt_tokens"), "completion_tokens": usage.get("completion_tokens"),
            "cache_tokens": usage.get("cache_tokens"), "total_tokens": usage.get("total_tokens"),
            "cost_usd": resolved_cost(usage, envelope), "error_class": classify_error(event, envelope),
            "envelope": event.get("envelope"),
        })
    rows.sort(key=lambda row: (str(row["model"]), str(row["task"]), int(row["seed"] or 0)))
    return plan, rows


def mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def fmt(value: Any, digits: int = 3) -> str:
    return "—" if value is None else f"{float(value):.{digits}f}"


def fmt_count(value: float | int) -> str:
    return f"{round(float(value)):,}"


_ARM_CONFIGS: dict[str, dict[str, Any]] = {}


def arm_config(arm: str) -> dict[str, Any]:
    """The arm's config, for the fields pricing needs.

    Without this an arm's own `price_per_mtok` — the documented escape hatch for
    a model LiteLLM has no entry for — was accepted by pricing.py and never
    reached it from here, so declaring a price changed nothing and the arm still
    reported "not priced".
    """
    if arm not in _ARM_CONFIGS:
        path = REPO / "evaluation" / "configs" / f"{arm}.json"
        _ARM_CONFIGS[arm] = load_json(path) if path.is_file() else {}
    return _ARM_CONFIGS[arm]


def resolved_cost(usage: dict[str, Any], envelope: dict[str, Any]) -> float | None:
    """Cost of a trial in USD, or None when its model has no known price.

    Prefers what the runtime recorded, and otherwise prices the recorded tokens
    here. Deriving it at report time means cost does not depend on every producer
    - the host proxy, a harbor agent, a future surface - remembering to compute
    it, and it prices runs that were recorded before any of them did.
    """
    recorded = usage.get("cost_usd")
    if isinstance(recorded, (int, float)) and recorded:
        return float(recorded)
    prompt = usage.get("prompt_tokens") or 0
    completion = usage.get("completion_tokens") or 0
    if not (prompt or completion):
        return None
    try:
        sys.path.insert(0, str(REPO / "evaluation" / "src"))
        import pricing
    except Exception:  # noqa: BLE001 - reporting must not fail over telemetry
        return None
    return pricing.cost_usd(str(envelope.get("model") or ""), prompt, completion,
                            str(envelope.get("provider") or ""),
                            arm_config=arm_config(str(envelope.get("arm") or "")),
                            cached_tokens=usage.get("cache_tokens") or 0)


def fmt_cost_cell(item: dict[str, Any]) -> str:
    """Dashboard cost cell — same honesty rule as the markdown total."""
    if not item.get("cost"):
        return "—"
    total = f"${item['cost']:.4f}"
    priced, measured = item.get("priced", 0), item.get("measured", 0)
    return total if priced >= measured else f"{total} <small>{priced}/{measured} priced</small>"


def fmt_cost(rows: list[dict[str, Any]]) -> str:
    """Total USD across rows, or an honest blank.

    A trial whose model has no known price contributes nothing and is counted, so
    a partial total is labelled rather than passed off as the arm's full cost —
    "$0.0000" next to a real figure would read as "this arm was free".
    """
    priced = [float(row["cost_usd"]) for row in rows
              if isinstance(row.get("cost_usd"), (int, float)) and row["cost_usd"]]
    if not priced:
        return "—"
    total = f"${sum(priced):.4f}"
    return total if len(priced) == len(rows) else f"{total} ({len(priced)}/{len(rows)} priced)"


def render_markdown(plan: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    planned = len(plan.get("tasks") or []) * len(plan.get("models") or []) * len(plan.get("seeds") or [])
    counts = Counter(str(row["status"]) for row in rows)
    lines = [
        f"# PersonaBench Pilot — {plan.get('suite_id', 'unknown')}", "",
        f"- Git SHA: `{plan.get('git_sha', 'unknown')}`",
        f"- Planned trials: **{planned}**; recorded: **{len(rows)}**",
        "- Status: " + (", ".join(f"`{key}`={value}" for key, value in sorted(counts.items())) or "none"),
        "",
        "## Leaderboard", "",
        "Ranking uses only task/seed cells with behavioral outcomes for every arm (common coverage). Scores are normalized to $[0,1]$.", "",
        "| Rank | Arm | Common mean | All behavioral mean | Full-pass rate | Common / planned | Infra errors | Avg time / task (s) | Avg model time / measured task (s) | Total tokens | Cost (USD) |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_model[str(row["model"])].append(row)
    models = [str(model) for model in plan.get("models") or by_model]
    behavioral_cells = {
        model: {(str(row.get("bucket") or ""), str(row["task"]),
             str(row.get("effort") or plan.get("effort") or "medium"), int(row["seed"] or 0))
                for row in by_model.get(model, [])
                if row["status"] in {"pass", "fail"} and row["normalized_reward"] is not None}
        for model in models
    }
    common_cells = set.intersection(*(behavioral_cells[model] for model in models)) if models else set()
    ranking = []
    for model, model_rows in by_model.items():
        behavioral = [row for row in model_rows if row["status"] in {"pass", "fail"} and row["normalized_reward"] is not None]
        scores = [float(row["normalized_reward"]) for row in behavioral]
        common = [row for row in behavioral
                  if (str(row.get("bucket") or ""), str(row["task"]),
                      str(row.get("effort") or plan.get("effort") or "medium"),
                      int(row["seed"] or 0)) in common_cells]
        common_scores = [float(row["normalized_reward"]) for row in common]
        durations = [float(row["duration_s"]) for row in model_rows
                 if isinstance(row["duration_s"], (int, float))]
        latencies = [float(row["model_latency_s"]) for row in model_rows if isinstance(row["model_latency_s"], (int, float))]
        tokens = [float(row["total_tokens"]) for row in model_rows if isinstance(row["total_tokens"], (int, float))]
        ranking.append((mean(common_scores) if common_scores else -1.0, model, common, behavioral,
                model_rows, durations, latencies, tokens))
    ranking.sort(reverse=True)
    for rank, (average, model, common, behavioral, model_rows, durations, latencies, tokens) in enumerate(ranking, 1):
        full = sum(row["status"] == "pass" for row in common)
        errors = sum(row["status"] not in {"pass", "fail"} for row in model_rows)
        pass_rate = full / len(common) if common else None
        lines.append(f"| {rank} | `{model}` | {fmt(average if average >= 0 else None)} | {fmt(mean([float(row['normalized_reward']) for row in behavioral]))} | {fmt(pass_rate)} | {len(common)} / {planned // max(1, len(models))} | {errors} | {fmt(mean(durations), 1)} | {fmt(mean(latencies), 1)} | {fmt_count(sum(tokens))} | {fmt_cost(model_rows)} |")

    publishable = len(common_cells) == (planned // max(1, len(models))) and not any(
        row["status"] not in {"pass", "fail"} for row in rows)
    lines.extend(["", f"**Comparable coverage:** {len(common_cells)}/{planned // max(1, len(models))} cells. "
                  + ("No infrastructure gaps detected." if publishable else "Not publishable until coverage gaps are resolved or the benchmark set is explicitly frozen.")])

    lines.extend(["", "## Performance by surface", "",
                  "Timing averages include every recorded attempt; total tokens sum tasks with reported usage.", "",
                  "| Surface | Tasks | Pass / Fail / Error | Avg time / task (s) | Avg passed task (s) | Total tokens |",
                  "|---|---:|---:|---:|---:|---:|"])
    for surface in ("survey", "chat", "web", "app"):
        surface_rows = [row for row in rows if row["surface"] == surface]
        surface_counts = Counter(str(row["status"]) for row in surface_rows)
        all_times = [float(row["duration_s"]) for row in surface_rows
                     if isinstance(row["duration_s"], (int, float))]
        pass_times = [float(row["duration_s"]) for row in surface_rows
                      if row["status"] == "pass" and isinstance(row["duration_s"], (int, float))]
        reported_tokens = [float(row["total_tokens"]) for row in surface_rows
                   if isinstance(row["total_tokens"], (int, float))]
        token_total = sum(reported_tokens) if reported_tokens else None
        errors = sum(surface_counts.get(status, 0) for status in ("error", "timeout", "preflight_error"))
        lines.append(f"| {surface.title()} | {len(surface_rows)} | {surface_counts.get('pass', 0)} / {surface_counts.get('fail', 0)} / {errors} | {fmt(mean(all_times), 1)} | {fmt(mean(pass_times), 1)} | {fmt_count(token_total) if token_total is not None else '—'} |")

    lines.extend(["", "## Task health", "", "| Task | Surface | Arm | Seed | Status | Score | Error class | Wall time (s) |", "|---|---|---|---:|---|---:|---|---:|"])
    for row in sorted(rows, key=lambda item: (str(item["task"]), str(item["model"]), int(item["seed"] or 0))):
        lines.append(f"| `{row['task']}` | {row['surface']} | `{row['model']}` | {row['seed']} | **{row['status']}** | {row['score'] or '—'} | {row['error_class'] or '—'} | {fmt(row['duration_s'], 1)} |")

    preflight = plan.get("preflight") if isinstance(plan.get("preflight"), dict) else {}
    broken = [(task, result) for task, result in preflight.items() if result.get("status") != "pass"]
    lines.extend(["", "## Preflight", "", f"Task contracts passing: **{len(preflight) - len(broken)}/{len(preflight)}**."])
    for task, result in broken:
        detail = str(result.get("detail", "")).splitlines()[-1] if result.get("detail") else "unknown"
        lines.append(f"- `{task}`: {detail}")
    lines.append("")
    return "\n".join(lines)


def render_html(plan: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    models = [str(model) for model in plan.get("models") or sorted({row["model"] for row in rows})]
    per_arm = len(plan.get("tasks") or []) * len(plan.get("seeds") or [])
    by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_model[str(row["model"])].append(row)

    def cell(row: dict[str, Any]) -> tuple[str, str, str, int]:
        return (str(row.get("bucket") or ""), str(row["task"]),
                str(row.get("effort") or plan.get("effort") or "medium"), int(row["seed"] or 0))

    behavioral_cells = {
        model: {cell(row) for row in by_model.get(model, [])
                if row["status"] in {"pass", "fail"} and row["normalized_reward"] is not None}
        for model in models
    }
    common_cells = set.intersection(*(behavioral_cells[model] for model in models)) if models else set()
    ranking = []
    for model in models:
        model_rows = by_model.get(model, [])
        behavioral = [row for row in model_rows
                      if row["status"] in {"pass", "fail"} and row["normalized_reward"] is not None]
        common = [row for row in behavioral if cell(row) in common_cells]
        score = mean([float(row["normalized_reward"]) for row in common])
        all_score = mean([float(row["normalized_reward"]) for row in behavioral])
        wall = mean([float(row["duration_s"]) for row in model_rows
                 if isinstance(row["duration_s"], (int, float))])
        latency = mean([float(row["model_latency_s"]) for row in model_rows
                        if isinstance(row["model_latency_s"], (int, float))])
        reported_tokens = [float(row["total_tokens"]) for row in model_rows
                   if isinstance(row["total_tokens"], (int, float))]
        tokens = sum(reported_tokens) if reported_tokens else None
        # A trial with no price must not read as a free one, so carry the count:
        # a total over 40 of 100 trials is not this arm's cost.
        priced_rows = [row for row in model_rows
                       if isinstance(row.get("cost_usd"), (int, float)) and row["cost_usd"]]
        cost = sum(float(row["cost_usd"]) for row in priced_rows) if priced_rows else None
        priced = len(priced_rows)
        errors = sum(row["status"] not in {"pass", "fail"} for row in model_rows)
        ranking.append({"model": model, "score": score, "all_score": all_score, "common": len(common),
                        "wall": wall, "latency": latency, "tokens": tokens, "cost": cost,
                        "priced": priced, "measured": len(model_rows), "errors": errors})
    ranking.sort(key=lambda item: (item["score"] is not None, item["score"] or -1), reverse=True)
    publishable = len(common_cells) == per_arm and not any(
        row["status"] not in {"pass", "fail"} for row in rows)

    leaderboard_rows = "".join(
        f"<tr><td><span class='rank'>{rank}</span></td><td class='arm'>{html.escape(item['model'])}</td>"
        f"<td class='score'>{fmt(item['score'])}</td><td>{fmt(item['all_score'])}</td>"
        f"<td>{item['common']} / {per_arm}</td><td>{item['errors']}</td><td>{fmt(item['wall'], 1)}</td>"
        f"<td>{fmt(item['latency'], 1)}</td><td>{fmt_count(item['tokens']) if item['tokens'] is not None else '—'}</td>"
        f"<td>{fmt_cost_cell(item)}</td></tr>"
        for rank, item in enumerate(ranking, 1)
    ) or "<tr><td colspan='10' class='empty'>No runtime trials recorded yet.</td></tr>"
    surface_rows = ""
    for surface in ("survey", "chat", "web", "app"):
        selected = [row for row in rows if row["surface"] == surface]
        surface_counts = Counter(str(row["status"]) for row in selected)
        durations = [float(row["duration_s"]) for row in selected
                     if isinstance(row["duration_s"], (int, float))]
        passed = [float(row["duration_s"]) for row in selected
                  if row["status"] == "pass" and isinstance(row["duration_s"], (int, float))]
        reported_tokens = [float(row["total_tokens"]) for row in selected
                   if isinstance(row["total_tokens"], (int, float))]
        token_total = sum(reported_tokens) if reported_tokens else None
        errors = sum(surface_counts.get(status, 0) for status in ("error", "timeout", "preflight_error"))
        surface_rows += (
            f"<tr><td><span class='surface-icon'>{surface[0].upper()}</span><b>{surface.title()}</b></td>"
            f"<td>{len(selected)}</td><td class='pass-text'>{surface_counts.get('pass', 0)}</td>"
            f"<td class='fail-text'>{surface_counts.get('fail', 0)}</td><td class='error-text'>{errors}</td>"
            f"<td><b>{fmt(mean(durations), 1)}s</b></td><td>{fmt(mean(passed), 1)}s</td>"
            f"<td>{fmt_count(token_total) if token_total is not None else '—'}</td></tr>"
        )
    health_rows = "".join(
        f"<tr data-status='{html.escape(str(row['status']))}' data-search='{html.escape(' '.join(str(row.get(key) or '') for key in ('task','surface','model','status','error_class')).lower())}'>"
        f"<td><div class='task'>{html.escape(str(row['task']))}</div><small>{html.escape(str(row.get('bucket') or ''))}</small></td>"
        f"<td>{html.escape(str(row['surface']))}</td><td>{html.escape(str(row['model']))}</td><td>{row['seed']}</td>"
        f"<td><span class='pill {html.escape(str(row['status']))}'>{html.escape(str(row['status']).upper())}</span></td>"
        f"<td>{html.escape(str(row['score'] or '—'))}</td><td>{fmt(row['duration_s'], 1)}</td>"
        f"<td>{fmt(row['model_latency_s'], 1)}</td><td>{fmt_count(row['total_tokens']) if isinstance(row['total_tokens'], (int, float)) else '—'}</td>"
        f"<td>{html.escape(str(row['error_class'] or '—'))}</td></tr>"
        for row in sorted(rows, key=lambda item: (str(item["task"]), str(item["model"]), int(item["seed"] or 0)))
    ) or "<tr><td colspan='10' class='empty'>No task results.</td></tr>"
    counts = Counter(str(row["status"]) for row in rows)
    status_summary = " · ".join(f"{html.escape(key)} {value}" for key, value in sorted(counts.items())) or "No trials"
    behavioral_count = counts.get("pass", 0) + counts.get("fail", 0)
    pass_rate = counts.get("pass", 0) / behavioral_count if behavioral_count else None
    avg_task_time = mean([float(row["duration_s"]) for row in rows
                          if isinstance(row["duration_s"], (int, float))])
    badge_class = "ready" if publishable else "warning"
    badge_text = "Publishable" if publishable else "Pilot / coverage incomplete"
    title = html.escape(str(plan.get("suite_id", "unknown")))
    sha = html.escape(str(plan.get("git_sha", "unknown")))
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>PersonaBench · {title}</title>
<style>
:root{{--bg:#07101f;--panel:#101b2d;--panel2:#142238;--line:#263852;--text:#edf4ff;--muted:#91a4bf;--cyan:#63d8ff;--green:#55e6a5;--amber:#ffc766;--red:#ff7c8d}}
*{{box-sizing:border-box}} body{{margin:0;background:radial-gradient(circle at 15% 0,#102b46 0,transparent 34%),var(--bg);color:var(--text);font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif}} .wrap{{max-width:1440px;margin:auto;padding:38px 28px 70px}} header{{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;margin-bottom:28px}} h1{{font-size:32px;letter-spacing:-.04em;margin:3px 0}} h2{{font-size:17px;margin:0 0 18px}} .eyebrow{{color:var(--cyan);font-weight:700;text-transform:uppercase;letter-spacing:.14em;font-size:11px}} .muted,small{{color:var(--muted)}} .badge{{padding:8px 12px;border-radius:99px;font-weight:700}} .badge.ready{{background:#123f35;color:var(--green)}} .badge.warning{{background:#46371a;color:var(--amber)}} .cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}} .card,.panel{{background:linear-gradient(145deg,rgba(20,34,56,.96),rgba(13,25,43,.96));border:1px solid var(--line);border-radius:16px;box-shadow:0 18px 45px rgba(0,0,0,.18)}} .card{{padding:18px}} .card b{{display:block;font-size:25px;margin-top:5px}} .panel{{padding:22px;margin-top:16px;overflow:hidden}} .table-wrap{{overflow:auto}} table{{width:100%;border-collapse:collapse;white-space:nowrap}} th{{color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.08em;text-align:left;padding:0 13px 11px}} td{{padding:13px;border-top:1px solid var(--line)}} tbody tr:hover{{background:rgba(99,216,255,.035)}} .rank{{display:inline-grid;place-items:center;width:26px;height:26px;border-radius:50%;background:#203652;color:var(--cyan)}} .arm,.score{{font-weight:750}} .score{{color:var(--green)}} .pill{{font-size:10px;font-weight:800;padding:5px 8px;border-radius:99px}} .pill.pass{{background:#123f35;color:var(--green)}} .pill.fail{{background:#473819;color:var(--amber)}} .pill.error,.pill.timeout,.pill.preflight_error{{background:#4a2230;color:var(--red)}} .toolbar{{display:flex;justify-content:space-between;align-items:center;gap:16px;margin-bottom:18px}} input{{width:min(390px,100%);background:#091526;border:1px solid var(--line);border-radius:10px;color:var(--text);padding:10px 13px;outline:none}} input:focus{{border-color:var(--cyan)}} .task{{max-width:530px;overflow:hidden;text-overflow:ellipsis}} .empty{{color:var(--muted);text-align:center;padding:30px}} footer{{color:var(--muted);margin-top:20px;font-size:12px}} @media(max-width:800px){{.cards{{grid-template-columns:repeat(2,1fr)}}header{{flex-direction:column}}}} 
</style><style>
:root{{--bg:#faf9ff;--panel:#fff;--panel2:#fff;--line:#e7e1f1;--text:#1b1930;--muted:#77748b;--cyan:#7137e8;--green:#15966d;--amber:#b87508;--red:#d94462}}
body{{background:radial-gradient(circle at 50% -12%,#ece4ff 0,transparent 38%),linear-gradient(#fcfbff,#f7f6fb);color:var(--text)}} body:before{{content:"";position:fixed;inset:0;pointer-events:none;opacity:.25;background-image:radial-gradient(#bdb3da 1px,transparent 1px);background-size:22px 22px}} .wrap{{position:relative;max-width:1440px;padding-top:50px}} header{{text-align:center;display:block;max-width:920px;margin:0 auto 34px}} h1{{font-size:34px;margin:10px 0 5px}} .eyebrow{{display:inline-flex;background:#eee7ff;border:1px solid #ddceff;border-radius:99px;padding:5px 12px;text-transform:none;letter-spacing:0}} .badge{{display:inline-flex;margin-top:14px;padding:6px 11px;font-size:12px}} .badge.ready{{background:#e6f7f0}} .badge.warning{{background:#fff3dd}} .card,.panel{{background:rgba(255,255,255,.94);border-color:var(--line);box-shadow:0 15px 45px rgba(71,43,125,.07)}} .card{{padding:20px}} .card b{{font-size:28px;letter-spacing:-.04em}} .card small{{display:block;margin-top:2px}} .panel{{border-radius:18px;padding:24px}} .section-head{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:18px}} .table-wrap{{border:1px solid var(--line);border-radius:13px}} th{{background:#fbfaff;color:#918da4;padding:11px 14px}} td{{border-color:var(--line);padding:14px}} tbody tr:hover{{background:#faf8ff}} .rank{{border-radius:9px;background:#eee7ff;color:var(--cyan);font-weight:800}} .score,.pass-text{{color:var(--green)}} .fail-text{{color:var(--amber)}} .error-text{{color:var(--red)}} .surface-icon{{display:inline-grid;place-items:center;width:28px;height:28px;margin-right:9px;border-radius:9px;background:#f1ecff;color:var(--cyan);font-weight:800}} .pill.pass{{background:#e6f7f0}} .pill.fail{{background:#fff3dd}} .pill.error,.pill.timeout,.pill.preflight_error{{background:#ffe9ee}} input{{background:#faf9ff;border-color:var(--line);border-radius:12px;color:var(--text)}} input:focus{{border-color:#9a6cff;box-shadow:0 0 0 3px #eee7ff}} .filters{{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:14px}} .filter-btn{{border:1px solid var(--line);background:#fff;color:var(--muted);padding:7px 12px;border-radius:99px;cursor:pointer;font-weight:650}} .filter-btn.active{{background:var(--cyan);border-color:var(--cyan);color:#fff}} footer{{text-align:center}} @media(max-width:850px){{.cards{{grid-template-columns:repeat(2,1fr)}}.toolbar,.section-head{{align-items:stretch;flex-direction:column}}}} @media(max-width:520px){{.cards{{grid-template-columns:1fr}}}}
</style></head><body><div class="wrap">
<header><div class="eyebrow">PersonaBench · Evaluation report</div><h1>{title}</h1><div class="muted">Git {sha} · {status_summary}</div><span class="badge {badge_class}">{badge_text}</span></header>
<section class="cards"><div class="card"><span class="muted">Recorded tasks</span><b>{len(rows)}</b><small>All attempted trials</small></div><div class="card"><span class="muted">Runnable tasks</span><b>{behavioral_count} / {len(rows)}</b><small>Pass + fail; no infra error</small></div><div class="card"><span class="muted">Behavioral pass rate</span><b>{fmt(pass_rate * 100 if pass_rate is not None else None, 1)}%</b><small>{counts.get('pass',0)} passed of {behavioral_count}</small></div><div class="card"><span class="muted">Avg time / task</span><b>{fmt(avg_task_time, 1)}s</b><small>All recorded attempts</small></div></section>
<section class="panel"><div class="section-head"><div><h2>Model leaderboard</h2><span class="muted">Ranked on common behavioral coverage</span></div></div><div class="table-wrap"><table><thead><tr><th>Rank</th><th>Model arm</th><th>Common score</th><th>All score</th><th>Runnable coverage</th><th>Infra errors</th><th>Avg time / task</th><th>Avg model / measured task</th><th>Total tokens</th><th>Total cost</th></tr></thead><tbody>{leaderboard_rows}</tbody></table></div></section>
<section class="panel"><div class="section-head"><div><h2>Performance by task type</h2><span class="muted">Timing averages include every attempt; token totals include reported telemetry only</span></div></div><div class="table-wrap"><table><thead><tr><th>Task type</th><th>Tasks</th><th>Pass</th><th>Fail</th><th>Error</th><th>Avg time / task</th><th>Avg passed task</th><th>Total tokens</th></tr></thead><tbody>{surface_rows}</tbody></table></div></section>
<section class="panel"><div class="toolbar"><div><h2>Task health</h2><span class="muted">Inspect individual outcomes and measured usage</span></div><input id="filter" placeholder="Search task, type, model, or status…"></div><div class="filters"><button class="filter-btn active" data-status="">All</button><button class="filter-btn" data-status="pass">Pass</button><button class="filter-btn" data-status="fail">Fail</button><button class="filter-btn" data-status="error">Error</button></div><div class="table-wrap"><table id="health"><thead><tr><th>Task</th><th>Type</th><th>Model arm</th><th>Seed</th><th>Status</th><th>Score</th><th>Total time</th><th>Model time</th><th>Task tokens</th><th>Error class</th></tr></thead><tbody>{health_rows}</tbody></table></div></section>
<footer>Generated from the immutable suite plan and append-only trial events · Scores normalized to [0,1]</footer>
</div><script>const f=document.getElementById('filter'),buttons=[...document.querySelectorAll('.filter-btn')];let status='';function apply(){{const q=f.value.toLowerCase();document.querySelectorAll('#health tbody tr[data-search]').forEach(r=>r.hidden=!r.dataset.search.includes(q)||(status&&r.dataset.status!==status))}}f.addEventListener('input',apply);buttons.forEach(b=>b.addEventListener('click',()=>{{buttons.forEach(x=>x.classList.remove('active'));b.classList.add('active');status=b.dataset.status;apply()}}));</script></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite_id")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    suite_dir = SUITES / args.suite_id
    if not (suite_dir / "plan.json").is_file():
        raise SystemExit(f"error: suite not found: {suite_dir.relative_to(REPO)}")
    output = args.output_dir or suite_dir
    output.mkdir(parents=True, exist_ok=True)
    plan, rows = build_rows(suite_dir)
    (output / "summary.json").write_text(json.dumps({"plan": plan, "trials": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = list(rows[0]) if rows else ["run_key", "task", "model", "seed", "status"]
    with (output / "trials.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    report = render_markdown(plan, rows)
    (output / "leaderboard.md").write_text(report, encoding="utf-8")
    (output / "leaderboard.html").write_text(render_html(plan, rows), encoding="utf-8")
    print(f"Wrote {output / 'leaderboard.md'}")
    print(f"Wrote {output / 'leaderboard.html'}")
    print(f"Wrote {output / 'trials.csv'}")
    print(f"Wrote {output / 'summary.json'}")


if __name__ == "__main__":
    main()
