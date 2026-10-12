#!/usr/bin/env python3
"""Aggregate every recorded run into one standing leaderboard.

`report_suite.py` reports one suite. This walks all of them and keeps a single
cross-model view that grows as runs land:

    leaderboard/index.html        the comparison page
    leaderboard/models/<arm>.md   one file per arm, its full record
    leaderboard/leaderboard.json  the same data, machine-readable

Two things it refuses to blur, because they are what make a comparison wrong:

* **Coverage.** A run that did not finish is kept and shown, but never ranked -
  a mean over the 40 tasks an arm happened to complete is not its score.
* **The judge.** 32 of these tasks are scored by an LLM judge, so arms judged by
  different models are not on the same scale. They are grouped by judge, and a
  cross-judge comparison is labelled rather than silently ranked.

Run it after any suite finishes — no arguments, no suite id to remember:

    python evaluation/leaderboard.py

It re-renders every suite's own report from its envelopes first, so a run that
finished a minute ago is included without a separate report_suite.py step.
"""
from __future__ import annotations

import argparse
import csv
import html
import json
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
SUITES = REPO / "evaluation" / "results" / "suites"
SURFACES = ("survey", "chat", "web", "app")

# How many attributes a task pins. Short labels for the column heads; the full
# ids are what the results tree and trials.csv use.
BUCKETS = ("single-attribute", "multi-attribute")
BUCKET_LABELS = {"single-attribute": "single", "multi-attribute": "multi"}

# Vendor marks for the ranking, keyed by the `provider` id an arm config
# records. Same source and same colour table as the deployment app's own
# leaderboard (playground/frontend/src/components/leaderboard/vendorLogos.tsx),
# so a model wears the same mark on both surfaces.
#
# The SVGs live in ASSETS, vendored by tools/fetch_vendor_icons.sh, and are
# INLINED at render time: the page has to open from disk with no network, so a
# CDN link would leave a hole in it offline.
#
# `tile` is the vendor's brand colour and `mark` the colour drawn on it - white
# except where the brand is black-on-white, which needs `ring` too or the tile
# vanishes against the card. `initial` is the fallback for a provider with no
# icon. These are the vendors' trademarks, used to identify whose model each row
# is; that is nominative use in a comparison, not endorsement.
ASSETS = REPO / "evaluation" / "assets" / "vendors"

VENDORS: dict[str, dict[str, Any]] = {
    "anthropic":  {"label": "Anthropic",  "initial": "A", "tile": "#D97757", "mark": "#FFFFFF", "icon": "anthropic"},
    "openai":     {"label": "OpenAI",     "initial": "O", "tile": "#FFFFFF", "mark": "#000000", "icon": "openai", "ring": True},
    "gemini":     {"label": "Google",     "initial": "G", "tile": "#4285F4", "mark": "#FFFFFF", "icon": "gemini"},
    "google":     {"label": "Google",     "initial": "G", "tile": "#4285F4", "mark": "#FFFFFF", "icon": "gemini"},
    "dashscope":  {"label": "Qwen",       "initial": "Q", "tile": "#6950EF", "mark": "#FFFFFF", "icon": "dashscope"},
    "zai":        {"label": "Z.ai",       "initial": "Z", "tile": "#1F6FEB", "mark": "#FFFFFF", "icon": "zai"},
    "deepseek":   {"label": "DeepSeek",   "initial": "D", "tile": "#4D6BFE", "mark": "#FFFFFF", "icon": "deepseek"},
    "openrouter": {"label": "OpenRouter", "initial": "R", "tile": "#0F172A", "mark": "#FFFFFF", "icon": "openrouter"},
    "xai":        {"label": "xAI",        "initial": "X", "tile": "#000000", "mark": "#FFFFFF"},
}


# Tiers that name a size rather than a family. On its own "opus-4-8" says
# nothing about whose model it is, so the family goes in front and the tier
# moves to the end: claude-4.8-opus.
FAMILY_OF_TIER = {"opus": "claude", "sonnet": "claude", "haiku": "claude", "fable": "claude"}


def display_name(arm: str) -> str:
    """The arm id written the way the model is normally named.

    Arm ids are filesystem- and CLI-safe: lowercase, hyphenated, and sometimes
    carrying the host so two deployments of one model can coexist. None of that
    belongs in the name a reader sees, so this undoes it:

    * `4-8` -> `4.8`. Only a hyphen BETWEEN two digits is a disguised decimal
      point - the ones in `glm-5-3-flash` separate words - so the substitution
      is anchored on digits at both ends.
    * a trailing `-azure` and friends go: the tile and the runs table already
      say where it ran, and the host is not part of the model's name.
    * a bare tier gains its family and moves to the end: `Claude-4.8-Opus`.
    * segments are capitalised, with the acronyms uppercased outright.

    The raw id stays the identifier everywhere it is one - the models/ filename,
    the runs table, the value passed to `--model`.
    """
    name = re.sub(r"(?<=\d)-(?=\d)", ".", arm.strip().lower())
    for host in HOSTS:
        if name.endswith("-" + host):
            name = name[: -len(host) - 1]
            break
    tier, _, rest = name.partition("-")
    family = FAMILY_OF_TIER.get(tier)
    if family and rest:
        name = f"{family}-{rest}-{tier}"
    return "-".join(_cap(part) for part in name.split("-"))


# Words whose casing is not "first letter up": acronyms, and the brands that
# carry a capital in the middle. Title-casing is only the fallback.
WORD_CASE = {
    "gpt": "GPT", "glm": "GLM", "ai": "AI",
    "deepseek": "DeepSeek", "openai": "OpenAI", "xai": "xAI",
}


def _cap(part: str) -> str:
    fixed = WORD_CASE.get(part.lower())
    if fixed:
        return fixed
    if part and part[0].isdigit():   # a version segment stays exactly as it is
        return part
    return part[:1].upper() + part[1:]



_GLYPHS: dict[str, str] = {}


def vendor_glyph(icon: str) -> str:
    """The vendor's logo as inline SVG, or '' when there is no icon for it.

    Each upstream file is a single monochrome path drawing in `currentColor`, so
    the tile sets the colour once and the mark follows. The file's <title> is
    dropped: the tile already carries the vendor name as a tooltip, and a second
    accessible name inside it would be announced twice.
    """
    if not icon:
        return ""
    if icon not in _GLYPHS:
        path = ASSETS / f"{icon}.svg"
        try:
            svg = path.read_text(encoding="utf-8").strip()
        except OSError:
            _GLYPHS[icon] = ""
            return ""
        svg = re.sub(r"<title>.*?</title>", "", svg, flags=re.S)
        # Upstream sizes itself at 1em with an inline flex style; strip both so
        # the tile's own CSS decides how big the mark is.
        svg = re.sub(r'\s(?:width|height)="1em"', "", svg)
        svg = re.sub(r'\sstyle="[^"]*"', "", svg)
        svg = svg.replace("<svg ", '<svg class="glyph" aria-hidden="true" ', 1)
        _GLYPHS[icon] = svg
    return _GLYPHS[icon]


# Providers that only HOST someone else's model. `provider` names where the
# request goes, which for these is not who made the model: gpt-6-astra on Azure
# AI Foundry is OpenAI's model, and a row that marks it "azure" tells the reader
# nothing about what is being compared. For these the vendor is read off the
# model name instead; the hosting still shows in the tooltip and in the arm id.
HOSTS = {"azure", "openrouter", "bedrock", "vertex_ai"}

# Model-name prefix -> the VENDORS key that made it.
MODEL_VENDOR: tuple[tuple[str, str], ...] = (
    ("gpt-", "openai"), ("o1", "openai"), ("o3", "openai"), ("o4", "openai"),
    ("claude", "anthropic"), ("opus", "anthropic"), ("sonnet", "anthropic"),
    ("haiku", "anthropic"), ("fable", "anthropic"),
    ("gemini", "gemini"),
    ("qwen", "dashscope"),
    ("glm", "zai"),
    ("deepseek", "deepseek"),
)


def vendor_of(provider: str | None, model: str | None = None) -> dict[str, Any]:
    """The vendor mark for an arm, with a neutral fallback.

    An unregistered provider still gets a tile - its initial on a neutral slate
    - so a new arm never renders as a hole in the ranking.
    """
    key = (provider or "").strip().lower()
    if key in HOSTS:
        name = (model or "").strip().lower()
        for prefix, vendor in MODEL_VENDOR:
            if name.startswith(prefix):
                # Keep the host visible; only the mark and label come from the maker.
                return {**VENDORS[vendor], "host": key}
    if key in VENDORS:
        return VENDORS[key]
    return {"label": provider or "unknown", "initial": (key[:1] or "?").upper(),
            "tile": "#64748B", "mark": "#FFFFFF", "icon": ""}


# --------------------------------------------------------------------------
# collect
# --------------------------------------------------------------------------
def refresh_suite_reports() -> list[str]:
    """Re-render each suite's trials.csv from its envelopes before aggregating.

    The alternative is remembering to run report_suite.py for the right suite id
    after every run, and a leaderboard built from a stale trials.csv is worse than
    no leaderboard. Rendering is cheap and idempotent, so it always runs; a suite
    that cannot be rendered is skipped rather than taking the whole update down.
    """
    sys.path.insert(0, str(REPO / "evaluation"))
    try:
        import report_suite
    except ImportError:
        return []
    refreshed = []
    for suite_dir in sorted(SUITES.iterdir() if SUITES.is_dir() else []):
        if not (suite_dir / "plan.json").is_file() or not (suite_dir / "events.jsonl").is_file():
            continue
        try:
            # An imported suite keeps its trials.csv but not its per-trial
            # envelopes — those live in the repo it was run from. Re-rendering it
            # here would read whatever sits at the same relative paths in THIS
            # checkout (a different arm's envelopes) or nothing at all, and
            # silently replace a correct table with a wrong one. Refresh only
            # what this checkout actually holds the evidence for.
            events = [json.loads(line) for line in
                      (suite_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
                      if line.strip()]
            envelopes = [e.get("envelope") for e in events if e.get("envelope")]
            if envelopes:
                present = sum(1 for e in envelopes if (REPO / e).is_file())
                if present < len(envelopes) / 2:
                    continue
            plan, rows = report_suite.build_rows(suite_dir)
            if not rows:
                continue
            fields = list(rows[0])
            with (suite_dir / "trials.csv").open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            (suite_dir / "leaderboard.md").write_text(
                report_suite.render_markdown(plan, rows), encoding="utf-8")
            refreshed.append(suite_dir.name)
        except Exception as exc:  # noqa: BLE001 - one bad suite must not block the rest
            print(f"  skipped {suite_dir.name}: {type(exc).__name__}: {exc}", file=sys.stderr)
    return refreshed


def load_runs() -> list[dict[str, Any]]:
    """One record per (suite, arm) that produced trials."""
    runs: list[dict[str, Any]] = []
    for suite_dir in sorted(SUITES.iterdir() if SUITES.is_dir() else []):
        trials = suite_dir / "trials.csv"
        plan_path = suite_dir / "plan.json"
        if not trials.is_file() or not plan_path.is_file():
            continue
        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            rows = list(csv.DictReader(trials.open(encoding="utf-8")))
        except (OSError, json.JSONDecodeError, csv.Error):
            continue
        if not rows:
            continue
        planned_per_arm = len(plan.get("tasks") or []) * max(1, len(plan.get("seeds") or [0]))
        credentials = (plan.get("runtime_readiness") or {}).get("credentials") or {}
        by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_arm[row["model"]].append(row)
        for arm, arm_rows in by_arm.items():
            judge = credentials.get(f"{arm} (llm judge)") or {}
            arm_config = (plan.get("arm_configs") or {}).get(arm, {})
            planned_tasks = {str(t.get("task")) for t in (plan.get("tasks") or [])
                             if t.get("task")}
            runs.append(summarize(suite_dir.name, plan, arm, arm_rows,
                                  planned_per_arm, judge, arm_config, planned_tasks))
    return runs


def _num(row: dict[str, Any], key: str) -> float | None:
    value = row.get(key)
    if value in (None, "", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def summarize(suite: str, plan: dict[str, Any], arm: str, rows: list[dict[str, Any]],
              planned: int, judge: dict[str, Any], arm_config: dict[str, Any],
              planned_tasks: set[str] | None = None) -> dict[str, Any]:
    planned_tasks = planned_tasks or set()
    behavioral = [r for r in rows if r["status"] in {"pass", "fail"}]
    rewards = [_num(r, "normalized_reward") or 0.0 for r in behavioral]
    errors = [r for r in rows if r["status"] not in {"pass", "fail"}]
    priced = [c for c in (_num(r, "cost_usd") for r in rows) if c]
    tokens = [t for t in (_num(r, "total_tokens") for r in rows) if t]
    durations = [d for d in (_num(r, "duration_s") for r in rows) if d is not None]

    surfaces = {}
    for surface in SURFACES:
        sub = [r for r in rows if r["surface"] == surface]
        if not sub:
            continue
        sub_beh = [r for r in sub if r["status"] in {"pass", "fail"}]
        surfaces[surface] = {
            "tasks": len(sub),
            "pass": sum(r["status"] == "pass" for r in sub),
            "fail": sum(r["status"] == "fail" for r in sub),
            "error": sum(r["status"] not in {"pass", "fail"} for r in sub),
            "mean": (statistics.mean(_num(r, "normalized_reward") or 0.0 for r in sub_beh)
                     if sub_beh else None),
        }

    return {
        "arm": arm,
        "suite": suite,
        "model": arm_config.get("model") or arm,
        "provider": arm_config.get("provider") or "",
        "endpoint": arm_config.get("base_url") or "",
        "git_sha": (plan.get("git_sha") or "")[:8],
        "run_at": plan.get("created_at") or "",
        "effort": plan.get("effort") or "",
        "seeds": plan.get("seeds") or [],
        "judge_model": judge.get("model") or "",
        "judge_provider": judge.get("provider") or "",
        "planned": planned,
        "recorded": len(rows),
        "complete": len(rows) >= planned > 0,
        "measured": len(behavioral),
        "pass": sum(r["status"] == "pass" for r in rows),
        "fail": sum(r["status"] == "fail" for r in rows),
        "error": len(errors),
        "mean": statistics.mean(rewards) if rewards else None,
        "full_pass_rate": (sum(r["status"] == "pass" for r in behavioral) / len(behavioral)
                           if behavioral else None),
        "surfaces": surfaces,
        "tokens": sum(tokens) if tokens else None,
        "cost": sum(priced) if priced else None,
        "priced": len(priced),
        "wall_s": sum(durations) if durations else None,
        "error_classes": dict(Counter(r.get("error_class") or "unclassified" for r in errors)),
        "planned_tasks": planned_tasks,
        "verdicts": [
            {"task": r["task"], "surface": r["surface"], "bucket": r["bucket"],
             "status": r["status"],
             "score": r.get("score") or "", "reward": _num(r, "normalized_reward"),
             "seconds": _num(r, "duration_s"), "cost": _num(r, "cost_usd"),
             "tokens": _num(r, "total_tokens"),
             "error_class": r.get("error_class") or ""}
            for r in sorted(rows, key=lambda r: (SURFACES.index(r["surface"])
                                                 if r["surface"] in SURFACES else 9, r["task"]))
        ],
    }


# Tasks every arm holds carry no ranking signal: they move every mean by the
# same amount and separate nobody. This many of them are dropped from the shared
# set, spread evenly over the non-app surfaces, so the reported spread reflects
# where the arms actually differ. NOT a deletion - the tasks still run, still
# appear in the per-task field, and still sit in the results tree; only the
# ranking ignores them. The page says so, because pruning only tasks that
# everyone passed lowers every score and would otherwise read as the arms
# getting worse.
# Off by default. Dropping tasks every arm held sharpens the spread between
# arms, but it also lowers every score, so it is a deliberate analysis choice
# rather than a default the benchmark should make for its readers. Set a count
# to enable it; the page says how many were set aside when it is on.
SATURATED_DROPPED = 0
SATURATED_SURFACES = ("web", "chat", "survey")


def drop_saturated(common: set[str], verdicts_by_arm: list[list[dict[str, Any]]],
                   surface_of: dict[str, str]) -> set[str]:
    """The tasks to exclude: `SATURATED_DROPPED` that every arm held.

    Split as evenly as the pools allow, and inside a surface taken round-robin
    over attribute families rather than alphabetically - a straight sort would
    take every `interests-topics` task first and quietly remove a whole
    dimension from the comparison.
    """
    held = [{v["task"] for v in vs if v["task"] in common and v["status"] == "pass"}
            for vs in verdicts_by_arm]
    if not held:
        return set()
    saturated = set.intersection(*held)

    pools: dict[str, list[str]] = {}
    for surface in SATURATED_SURFACES:
        by_family: dict[str, list[str]] = {}
        for task in sorted(t for t in saturated if surface_of.get(t) == surface):
            family = task.split("/")[0] if "/" in task else task.rsplit("-", 1)[0]
            by_family.setdefault(family, []).append(task)
        ordered: list[str] = []
        while any(by_family.values()):        # one from each family, then round again
            for family in sorted(by_family):
                if by_family[family]:
                    ordered.append(by_family[family].pop(0))
        pools[surface] = ordered

    # Largest pools absorb the remainder, so no surface is asked for more than
    # it has while another sits on spares.
    order = sorted(SATURATED_SURFACES, key=lambda s: -len(pools[s]))
    take = {s: 0 for s in order}
    remaining = min(SATURATED_DROPPED, sum(len(pools[s]) for s in order))
    # Hand out in rounds rather than one pass with a running shortfall: a single
    # pass can only push spare capacity forward, so a small pool later in the
    # order strands slots that an earlier, larger pool could have absorbed.
    while remaining:
        open_pools = [s for s in order if take[s] < len(pools[s])]
        if not open_pools:
            break
        share = max(1, remaining // len(open_pools))
        for surface in open_pools:
            if not remaining:
                break
            n = min(share, len(pools[surface]) - take[surface], remaining)
            take[surface] += n
            remaining -= n
    chosen: set[str] = set()
    for surface in order:
        chosen.update(pools[surface][:take[surface]])
    return chosen


def latest_per_arm(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One record per arm, merging its suites by task.

    An arm's run is often split across suites — survey/chat/web in one, app in
    another, a retry in a third. Taking only the newest suite would hide the
    other surfaces entirely, so this keeps the newest trial for each individual
    task and rebuilds the arm from those. Planned coverage is the union of the
    task lists of every suite that ran the arm, which is what makes a partial
    run visible as partial rather than as a small complete one.
    """
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for run in runs:
        by_arm[run["arm"]].append(run)

    merged = []
    for arm, arm_runs in by_arm.items():
        arm_runs.sort(key=lambda r: r["run_at"])          # oldest first
        newest_verdict: dict[str, dict[str, Any]] = {}
        planned_tasks: set[str] = set()
        for run in arm_runs:                              # later suites win
            for verdict in run["verdicts"]:
                newest_verdict[verdict["task"]] = verdict
            planned_tasks.update(run["planned_tasks"])
        latest = arm_runs[-1]
        record = dict(latest)
        record["verdicts"] = sorted(
            newest_verdict.values(),
            key=lambda v: (SURFACES.index(v["surface"]) if v["surface"] in SURFACES else 9,
                           v["task"]))
        record["suites"] = [r["suite"] for r in arm_runs]
        record["suite"] = ", ".join(record["suites"])
        record.update(aggregate(record["verdicts"], len(planned_tasks)))
        merged.append(record)

    # Rank on the tasks EVERY arm scored behaviourally, not on each arm's own
    # mean. Arms are scored by harnesses that disagree about what counts as
    # scorable — the old one recorded an app trial with no artifact as fail
    # (reward 0), the current one records it as error (excluded) — so an arm can
    # be punished for exactly the condition another is excused from. Restricting
    # to the shared set removes that, and states the coverage it used.
    scorable = [
        {v["task"] for v in r["verdicts"] if v["status"] in {"pass", "fail"}}
        for r in merged
    ]
    common = set.intersection(*scorable) if scorable else set()
    surface_of = {v["task"]: v["surface"] for r in merged for v in r["verdicts"]}
    dropped = drop_saturated(common, [r["verdicts"] for r in merged], surface_of)
    common -= dropped
    for record in merged:
        in_common = [v for v in record["verdicts"]
                     if v["task"] in common and v["status"] in {"pass", "fail"}]
        record["common_mean"] = (statistics.mean(v["reward"] or 0.0 for v in in_common)
                                 if in_common else None)
        record["common_n"] = len(in_common)
        record["ranked_tasks"] = common
        record["saturated_dropped"] = len(dropped)
        # Everything shown beside the headline is scoped to the same tasks the
        # headline is computed on. Mixing a shared-set mean with all-task counts
        # in one line invites reading them as the same measurement.
        record["common_pass"] = sum(v["status"] == "pass" for v in in_common)
        record["common_fail"] = sum(v["status"] == "fail" for v in in_common)
        priced = [v["cost"] for v in in_common if v.get("cost")]
        record["common_cost"] = sum(priced) if priced else None
        record["common_priced"] = len(priced)
        record["common_tokens"] = sum(v["tokens"] for v in in_common if v.get("tokens")) or None
        # How many of the scored trials actually recorded usage. An arm whose
        # result tree was imported without its per-trial artifacts still has a
        # token sum, but over a fraction of its trials - reporting that as the
        # arm's total makes the most expensive model look like the cheapest.
        record["common_token_trials"] = sum(1 for v in in_common if v.get("tokens"))
        record["common_surfaces"] = {
            surface: statistics.mean(v["reward"] or 0.0 for v in group)
            for surface in SURFACES
            if (group := [v for v in in_common if v["surface"] == surface])
        }
        # The same shared set cut the other way: how many attributes the task
        # pinned. Computed here, not in summarize, so it is scoped to exactly
        # the tasks the headline is - a bucket mean over each arm's own tasks
        # would not be comparable for the same reason the raw means are not.
        record["common_buckets"] = {
            bucket: statistics.mean(v["reward"] or 0.0 for v in group)
            for bucket in BUCKETS
            if (group := [v for v in in_common if v.get("bucket") == bucket])
        }

    return sorted(merged,
                  key=lambda r: (r["complete"],
                                 r["common_mean"] if r["common_mean"] is not None else -1),
                  reverse=True)


def aggregate(verdicts: list[dict[str, Any]], planned: int) -> dict[str, Any]:
    """Headline numbers over a set of verdicts — shared by one suite and by a merge."""
    behavioral = [v for v in verdicts if v["status"] in {"pass", "fail"}]
    rewards = [v["reward"] or 0.0 for v in behavioral]
    surfaces = {}
    for surface in SURFACES:
        sub = [v for v in verdicts if v["surface"] == surface]
        if not sub:
            continue
        sub_beh = [v for v in sub if v["status"] in {"pass", "fail"}]
        surfaces[surface] = {
            "tasks": len(sub),
            "pass": sum(v["status"] == "pass" for v in sub),
            "fail": sum(v["status"] == "fail" for v in sub),
            "error": sum(v["status"] not in {"pass", "fail"} for v in sub),
            "mean": (statistics.mean(v["reward"] or 0.0 for v in sub_beh)
                     if sub_beh else None),
        }
    priced = [v["cost"] for v in verdicts if v.get("cost")]
    seconds = [v["seconds"] for v in verdicts if v.get("seconds") is not None]
    return {
        "planned": planned,
        "recorded": len(verdicts),
        "complete": len(verdicts) >= planned > 0,
        "measured": len(behavioral),
        "pass": sum(v["status"] == "pass" for v in verdicts),
        "fail": sum(v["status"] == "fail" for v in verdicts),
        "error": sum(v["status"] not in {"pass", "fail"} for v in verdicts),
        "mean": statistics.mean(rewards) if rewards else None,
        "full_pass_rate": (sum(v["status"] == "pass" for v in behavioral) / len(behavioral)
                           if behavioral else None),
        "surfaces": surfaces,
        "cost": sum(priced) if priced else None,
        "priced": len(priced),
        "tokens": sum(v["tokens"] for v in verdicts if v.get("tokens")) or None,
        "wall_s": sum(seconds) if seconds else None,
        "error_classes": dict(Counter(v.get("error_class") or "unclassified"
                                      for v in verdicts
                                      if v["status"] not in {"pass", "fail"})),
    }


# --------------------------------------------------------------------------
# per-model markdown
# --------------------------------------------------------------------------
def fmt(value: float | None, places: int = 3) -> str:
    return "—" if value is None else f"{value:.{places}f}"


def pct(value: float | None, places: int = 1) -> str:
    """A [0,1] reward as a percentage, for the page.

    The markdown and JSON keep the raw fraction: those are read by machines and
    by anyone recomputing, and a percent sign there would just have to be parsed
    back off. This is the display form only.
    """
    return "—" if value is None else f"{value * 100:.{places}f}%"


def fmt_dur(seconds: float | None) -> str:
    if not seconds:
        return "—"
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m" if hours else f"{minutes}m{secs:02d}s"


def fmt_common_cost(run: dict[str, Any]) -> str:
    """Cost over the shared tasks only, so the whole line reads at one scope."""
    total, priced, n = run.get("common_cost"), run.get("common_priced", 0), run.get("common_n", 0)
    if not total:
        return "not priced"
    label = f"${total:.4f}"
    return label if priced >= n else f"{label} ({priced}/{n} priced)"


def fmt_cost(run: dict[str, Any]) -> str:
    if not run["cost"]:
        return "not priced"
    total = f"${run['cost']:.4f}"
    return total if run["priced"] >= run["recorded"] else f"{total} ({run['priced']}/{run['recorded']} priced)"


def model_markdown(run: dict[str, Any]) -> str:
    lines = [
        f"# {display_name(run['arm'])}",
        "",
        f"Arm id `{run['arm']}` \u2014 what you pass to `--model`.",
        "",
        f"`{run['model']}` on `{run['provider'] or 'unknown provider'}`"
        + (f", endpoint `{run['endpoint']}`" if run["endpoint"] else ""),
        "",
        "## Result",
        "",
        "| | |",
        "|---|---|",
        f"| Persona adherence | **{fmt(run['mean'])}** mean reward over {run['measured']} scored tasks |",
        f"| Held every check | {fmt(run['full_pass_rate'])} of scored tasks |",
        f"| Coverage | {run['recorded']} / {run['planned']} tasks"
        + ("" if run["complete"] else " — **incomplete, not ranked**") + " |",
        f"| Not scorable | {run['error']} tasks failed to run |",
        f"| Judge | `{run['judge_model'] or 'unknown'}`"
        + (f" on `{run['judge_provider']}`" if run["judge_provider"] else "") + " |",
        f"| Cost | {fmt_cost(run)} |",
        f"| Tokens | {int(run['tokens']):,} |" if run["tokens"] else "| Tokens | — |",
        f"| Task time | {fmt_dur(run['wall_s'])} across all trials |",
        f"| Run | `{run['suite']}` at `{run['git_sha']}`, effort {run['effort']}, "
        f"seed{'s' if len(run['seeds']) > 1 else ''} {', '.join(map(str, run['seeds']))} |",
        "",
        "## By surface",
        "",
        "| Surface | Tasks | Held | Violated | Not scorable | Mean reward |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for surface, data in run["surfaces"].items():
        lines.append(f"| {surface} | {data['tasks']} | {data['pass']} | {data['fail']} | "
                     f"{data['error']} | {fmt(data['mean'])} |")

    if run["error_classes"]:
        lines += ["", "## What failed to run", "",
                  "These are infrastructure, not behaviour, and are excluded from the mean.",
                  "", "| Cause | Tasks |", "|---|---:|"]
        for cause, count in sorted(run["error_classes"].items(), key=lambda kv: -kv[1]):
            lines.append(f"| {cause} | {count} |")

    lines += ["", "## Every task", "",
              "| Task | Surface | Verdict | Score | Seconds |", "|---|---|---|---|---:|"]
    for verdict in run["verdicts"]:
        mark = {"pass": "held", "fail": "violated"}.get(verdict["status"], verdict["status"])
        lines.append(f"| `{verdict['task']}` | {verdict['surface']} | {mark} | "
                     f"{verdict['score'] or '—'} | {fmt(verdict['seconds'], 1)} |")
    lines += ["", f"_Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC "
              f"by `evaluation/leaderboard.py`._", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# the page
# --------------------------------------------------------------------------
CSS = """
/* Palette and vocabulary borrowed from the deployment app's leaderboard
   (playground/frontend/.../LeaderboardView.tsx): white cards on slate
   hairlines, a slate-50 header strip, one accent. The two surfaces show the
   same models, so they should not look like two different products. */
:root{
  --bg:#F8FAFC; --card:#FFFFFF;
  --ink:#0F172A; --ink-2:#475569; --ink-3:#94A3B8;
  --line:#E2E8F0; --line-soft:#F1F5F9; --strip:#F8FAFCB3;
  --accent:#6950EF; --held:#0F766E; --violated:#C2410C; --void:#CBD5E1;
  --shadow:0 1px 2px rgba(15,23,42,.06), 0 1px 3px rgba(15,23,42,.04);
  --measure:70ch;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{
  margin:0; background:var(--bg); color:var(--ink);
  font-family:"Inter",-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
  font-size:16px; line-height:1.55; font-variant-numeric:tabular-nums;
  -webkit-font-smoothing:antialiased;
}
.page{max-width:1080px; margin:0 auto; padding:clamp(2rem,5vw,4.5rem) clamp(1.1rem,4vw,2rem) 5rem}
a{color:var(--accent); text-decoration-thickness:1px; text-underline-offset:.18em}
a:focus-visible{outline:2px solid var(--accent); outline-offset:3px; border-radius:4px}

.eyebrow{
  display:inline-flex; align-items:center; gap:.5rem; margin:0 0 1rem;
  border:1px solid var(--line); background:var(--card); border-radius:99px;
  padding:.3rem .8rem; font-size:.75rem; font-weight:600; color:var(--ink-2);
  box-shadow:var(--shadow);
}
.eyebrow i{width:6px; height:6px; border-radius:99px; background:var(--accent)}
h1{font-size:clamp(1.9rem,4vw,2.6rem); font-weight:650; line-height:1.1; letter-spacing:-.025em; margin:0 0 .6rem}
.lede{max-width:var(--measure); font-size:1rem; color:var(--ink-2); margin:0}
.meta{color:var(--ink-3); font-size:.84rem; margin:.9rem 0 0}

h2{font-size:1.15rem; font-weight:650; letter-spacing:-.015em; margin:3.2rem 0 .35rem}
h2+p.note{max-width:var(--measure); color:var(--ink-2); font-size:.92rem; margin:0 0 1.1rem}

/* ---- the ranking card ------------------------------------------------------
   Header and rows share one grid template so every score column lines up under
   its label without a <table>; the identity cell has to wrap and stack, which a
   table cell does badly. --nbucket and --nsurf are set inline from the data, so
   a suite with no app tasks grows no empty app column. */
.board{
  margin:1.6rem 0 0; background:var(--card); border:1px solid var(--line);
  border-radius:16px; box-shadow:var(--shadow); overflow:hidden;
  --board-cols:2rem minmax(132px,1fr) 108px
               repeat(var(--nbucket,2),minmax(56px,68px))
               repeat(var(--nsurf,4),minmax(56px,70px))
               minmax(62px,76px);
}
.bhead,.brow{
  display:grid; grid-template-columns:var(--board-cols);
  align-items:center; gap:.5rem .85rem; padding:0 1.15rem;
}
.bhead{
  background:var(--strip); border-bottom:1px solid var(--line);
  padding-top:.6rem; padding-bottom:.6rem;
  font-size:.66rem; font-weight:600; letter-spacing:.08em;
  text-transform:uppercase; color:var(--ink-3);
}
.bhead span{text-align:right}
.bhead .h-who{grid-column:1 / 3; text-align:left}
.bhead .h-overall{color:var(--ink-2)}
/* The two attribute-count columns are a different cut of the same 354 tasks
   than the surface columns, so their heads are a shade darker — enough to read
   as a second group without a rule between them. */
.bhead .g-bucket{color:var(--ink-2)}
.brow{padding-top:.85rem; padding-bottom:.85rem; border-bottom:1px solid var(--line-soft); transition:background .12s}
.brow:last-child{border-bottom:0}
.brow:hover{background:var(--strip)}

.rank{font-size:1rem; font-weight:600; color:var(--ink); text-align:center}

.who{display:flex; align-items:center; gap:.7rem; min-width:0}
/* The mark is a single monochrome path taking `currentColor`, so the tile sets
   the colour once and the glyph follows. 55% leaves the optical margin a brand
   mark needs; filling the tile edge to edge reads as a crop. */
.tile{
  width:2rem; height:2rem; border-radius:9px; flex:none;
  display:grid; place-items:center; box-shadow:var(--shadow);
  font-size:.85rem; font-weight:700; line-height:1;
}
.tile.ring{box-shadow:var(--shadow), inset 0 0 0 1px var(--line)}
.tile .glyph{width:55%; height:55%; display:block; fill:currentColor}
.id{min-width:0}
.id a{
  display:block; font-size:.95rem; font-weight:600; letter-spacing:-.01em;
  color:var(--ink); text-decoration:none; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis;
}
.id a:hover{color:var(--accent)}
.id p{margin:.1rem 0 0; font-size:.78rem; color:var(--ink-3); white-space:nowrap; overflow:hidden; text-overflow:ellipsis}
.id b{font-weight:600; color:var(--ink-2)}
.chip{display:inline-block; border-radius:5px; background:var(--line-soft); padding:.05rem .35rem; font-size:.7rem; color:var(--ink-2); margin-right:.3rem}

.overall{text-align:right}
.overall .n{font-size:1.35rem; font-weight:700; letter-spacing:-.03em; line-height:1.1}

.sc{text-align:right; font-size:1rem; font-weight:600}
.sc.bucket{color:var(--ink)}
/* Cost carries a second line: the tokens that produced it. Same column, one
   step down in weight, so the row still scans as one number per column. */
.sc.cost .n{font-size:.95rem}
.sc.cost .sub{display:block; font-size:.72rem; font-weight:500; color:var(--ink-3); margin-top:.1rem}
/* A ~ figure covers less than half its trials; muted so it never reads
   as a like-for-like number beside a complete one. */
.sc.cost.partial .n{color:var(--ink-3); font-weight:600}
.sc.cost.none .n,.sc.cost.none .sub{color:var(--void)}
.bhead .h-cost small{font-size:.9em; font-weight:500; letter-spacing:.04em; text-transform:none}
.sc.none{color:var(--void); font-weight:500}
.sc.zero{color:var(--violated)}
.sc .lab{display:none}

.brow.unranked{background:#FFFBEB66}
.flag{
  display:inline-block; margin-left:.4rem; padding:.02rem .4rem; border-radius:5px;
  background:#FEF3C7; color:#92400E; font-size:.68rem; font-weight:600;
  vertical-align:middle; white-space:nowrap;
}

@media (max-width:900px){
  /* Below this the columns stop fitting: identity keeps the top line, the
     overall score sits under it, and the seven score columns become a labelled
     strip rather than seven unreadable slivers. */
  .board{--board-cols:2rem minmax(0,1fr)}
  .bhead{display:none}
  .brow .overall{grid-column:2 / -1; text-align:left}
  .brow .scores{grid-column:2 / -1; display:grid; grid-template-columns:repeat(auto-fit,minmax(56px,1fr)); gap:.7rem}
  .sc{text-align:left}
  .sc .lab{display:block; font-size:.62rem; font-weight:600; letter-spacing:.07em; text-transform:uppercase; color:var(--ink-3); margin-top:.15rem}
}
@media (min-width:901px){
  /* Wide: each score is its own grid column, so the wrapper mobile needs must
     not become a box of its own. */
  .brow .scores{display:contents}
}

/* ---- per-task field -------------------------------------------------------- */
.arm{background:var(--card); border:1px solid var(--line); border-radius:14px; box-shadow:var(--shadow); padding:.95rem 1.15rem; margin:0 0 .7rem}
.arm-name{font-size:.88rem; font-weight:650; color:var(--ink-2)}
.field{display:flex; flex-wrap:wrap; gap:2px; margin:.75rem 0 0}
.field .cell{width:11px; height:11px; border-radius:2px; background:var(--void)}
.field .held{background:var(--held)}
.field .violated{background:var(--violated)}
.field .unscored{background:transparent; box-shadow:inset 0 0 0 1px var(--void)}
.field .gap{width:9px; height:11px; background:none}

.legend{display:flex; flex-wrap:wrap; gap:1rem; color:var(--ink-3); font-size:.8rem; margin:1rem 0 0}
.legend span{display:flex; align-items:center; gap:.4rem}
.swatch{width:10px; height:10px; border-radius:2px; display:inline-block}

/* ---- runs table ------------------------------------------------------------ */
.scroll{overflow-x:auto; background:var(--card); border:1px solid var(--line); border-radius:14px; box-shadow:var(--shadow)}
table{width:100%; border-collapse:collapse; font-size:.85rem}
th{
  text-align:left; font-weight:600; font-size:.66rem; letter-spacing:.08em;
  text-transform:uppercase; color:var(--ink-3); background:var(--strip);
  border-bottom:1px solid var(--line); padding:.6rem .9rem; white-space:nowrap;
}
td{padding:.6rem .9rem; border-bottom:1px solid var(--line-soft); white-space:nowrap; color:var(--ink-2)}
tr:last-child td{border-bottom:0}
.num{text-align:right}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.85em; color:var(--ink)}

footer{margin-top:3.5rem; padding-top:1.1rem; border-top:1px solid var(--line); color:var(--ink-3); font-size:.82rem}
.empty{background:var(--card); border:1px dashed var(--line); border-radius:14px; padding:2rem; color:var(--ink-2); max-width:var(--measure)}
@media (prefers-reduced-motion:no-preference){
  .brow{animation:rise .4s cubic-bezier(.2,.7,.3,1) backwards}
  @keyframes rise{from{opacity:0; transform:translateY(4px)}}
}
"""

def verdict_field(run: dict[str, Any]) -> str:
    """One cell per task of the SCORED set, grouped by surface.

    Restricted to the tasks the ranking is computed on, so every arm's field is
    the same tasks in the same order and the rows can be read against each
    other. Showing everything an arm happened to run made them different
    lengths - one arm 471 cells, another 148 - which invites comparing shapes
    that are not the same picture.
    """
    ranked = run.get("ranked_tasks")
    cells = []
    last = None
    for verdict in run["verdicts"]:
        if ranked is not None and verdict["task"] not in ranked:
            continue
        if last is not None and verdict["surface"] != last:
            cells.append('<i class="gap"></i>')
        last = verdict["surface"]
        kind = {"pass": "held", "fail": "violated"}.get(verdict["status"], "unscored")
        label = {"held": "held", "violated": "violated"}.get(kind, verdict["status"])
        title = f'{verdict["task"]} — {label}'
        if verdict["score"]:
            title += f' ({verdict["score"]})'
        cells.append(f'<i class="cell {kind}" title="{html.escape(title)}"></i>')
    return f'<div class="field" role="img" aria-label="one cell per task, grouped by surface">{"".join(cells)}</div>'


def active(runs: list[dict[str, Any]], group: str,
           order: tuple[str, ...]) -> tuple[str, ...]:
    """The groups any recorded run actually has, in the canonical order.

    A suite that carries no app tasks should not grow a permanently empty app
    column: an all-em-dash column reads as "every arm failed here" rather than
    "this was never part of the suite".
    """
    present = {name for run in runs for name in (run.get(group) or {})}
    return tuple(name for name in order if name in present)


def fmt_tokens(total: float | None) -> str:
    """Token count at a glance: 33.1M rather than 33,083,379.

    The exact figure is in the runs table and in the arm's own file; in a column
    this narrow the magnitude is the only part anyone reads.
    """
    if not total:
        return "\u2014"
    if total >= 1e9:
        return f"{total / 1e9:.1f}B"
    if total >= 1e6:
        return f"{total / 1e6:.1f}M"
    if total >= 1e3:
        return f"{total / 1e3:.0f}K"
    return f"{int(total)}"


def cost_cell(run: dict[str, Any]) -> str:
    """What the shared tasks cost, over how many tokens.

    The two lines are gated separately because they fail separately: an arm can
    have a solid token count and still be mostly unpriced (a surface that logs a
    total but no prompt/completion split cannot be costed). A figure covering
    under half its trials is shown with a leading ~ and muted, never silently as
    if it were the arm's total - an undercount printed plainly next to a complete
    one is the one reading this column must not invite.
    """
    cost, tokens = run.get("common_cost"), run.get("common_tokens")
    priced, n = run.get("common_priced", 0), run.get("common_n", 0)
    counted = run.get("common_token_trials", 0)

    if not tokens:
        tok_line, tok_note = "no data", "no usage recorded"
    else:
        tok_line = fmt_tokens(tokens)
        tok_note = f"{int(tokens):,} tokens over {counted}/{n} trials"
        if n and counted * 2 < n:
            tok_line = f"~{tok_line}"

    partial = bool(n and priced * 2 < n)
    if cost:
        head = f"~${cost:.2f}" if partial else f"${cost:.2f}"
        cost_note = f"${cost:.4f} priced over {priced}/{n} trials"
        if partial:
            cost_note += " \u2014 a floor, not the total"
    else:
        head, cost_note = "\u2014", "no known price for this model"

    classes = "sc cost" + (" partial" if partial or (n and counted * 2 < n) else "")
    return (f"<div class='{classes}' title='{html.escape(cost_note + chr(183).join([" ", " "]) + tok_note)}'>"
            f"<span class='n'>{head}</span>"
            f"<span class='sub'>{tok_line}</span>"
            f"<span class='lab'>cost</span></div>")


def board_head(buckets: tuple[str, ...], surfaces: tuple[str, ...]) -> str:
    """Column labels for the ranking, on the same grid template as the rows."""
    cols = "".join(f"<span class='g-bucket'>{BUCKET_LABELS.get(b, b)}</span>" for b in buckets)
    cols += "".join(f"<span>{s}</span>" for s in surfaces)
    return (f"<div class='bhead'><span class='h-who'>Model</span>"
            f"<span class='h-overall'>Overall</span>{cols}"
            f"<span class='h-cost'>cost <small>(tokens)</small></span></div>")


def score_cell(run: dict[str, Any], group: str, name: str, extra: str = "") -> str:
    """One group's mean for one arm - a surface, or an attribute-count bucket.

    Reads the `common_*` maps, so every number in the row is over the same
    shared tasks as the headline beside it. A group with nothing in that set is
    an em dash, not 0.00: "not measured here" and "measured and lost" are
    different facts and must not look alike.
    """
    mean = (run.get(group) or {}).get(name)
    label = BUCKET_LABELS.get(name, name)
    classes = f"sc{extra}"
    if mean is None:
        return (f"<div class='{classes} none' title='{html.escape(label)} - not in the shared set'>"
                f"<span class='n'>\u2014</span><span class='lab'>{label}</span></div>")
    if mean == 0:
        classes += " zero"
    title = f"{label} - {pct(mean)} mean over the shared tasks"
    return (f"<div class='{classes}' title='{html.escape(title)}'>"
            f"<span class='n'>{pct(mean)}</span>"
            f"<span class='lab'>{label}</span></div>")


def vendor_tile(vendor: dict[str, Any]) -> str:
    """The vendor's brand tile: its mark on its colour, or its initial."""
    glyph = vendor_glyph(vendor.get("icon", "")) or html.escape(vendor["initial"])
    ring = " ring" if vendor.get("ring") else ""
    label = vendor["label"]
    if vendor.get("host"):
        label += f" \u00b7 hosted on {vendor['host']}"
    return (f"<span class='tile{ring}' "
            f"style='background:{vendor['tile']};color:{vendor['mark']}' "
            f"title='{html.escape(label)}'>{glyph}</span>")


def board_row(run: dict[str, Any], place: int | None,
              buckets: tuple[str, ...] = BUCKETS,
              surfaces: tuple[str, ...] = SURFACES) -> str:
    """One line of the ranking: place, vendor, arm, overall, then each cut.

    Every figure is over the shared task set, which is what makes the columns
    comparable across arms; each arm's own totals live in its own file.
    """
    vendor = vendor_of(run["provider"], run.get("model"))
    headline = run.get("common_mean")
    overall = ("<div class='overall'><span class='n'>\u2014</span></div>" if headline is None
               else f"<div class='overall'><span class='n'>{pct(headline)}</span></div>")
    flag = "" if run["complete"] else \
        f"<span class='flag'>{run['recorded']} of {run['planned']} \u2014 not ranked</span>"
    tally = (f"<b>{run.get('common_pass', 0)}</b> held \u00b7 "
             f"<b>{run.get('common_fail', 0)}</b> violated")
    sub = f"<span class='chip'>{html.escape(vendor['label'])}</span>{tally}"
    cells = "".join(score_cell(run, "common_buckets", b, " bucket") for b in buckets)
    cells += "".join(score_cell(run, "common_surfaces", s) for s in surfaces)
    cells += cost_cell(run)
    classes = "brow" + (" top" if place == 1 else "") + ("" if run["complete"] else " unranked")
    return f"""<div class="{classes}">
  <div class="rank">{place if place else '\u00b7'}</div>
  <div class="who">
    {vendor_tile(vendor)}
    <div class="id">
      <a href="models/{html.escape(run['arm'])}.md">{html.escape(display_name(run['arm']))}</a>{flag}
      <p>{sub}</p>
    </div>
  </div>
  {overall}
  <div class="scores">{cells}</div>
</div>"""


def arm_field(run: dict[str, Any]) -> str:
    """An arm's verdict field, below the ranking rather than inside it."""
    return (f'<article class="arm"><div class="arm-name">{html.escape(display_name(run["arm"]))}</div>'
            f'{verdict_field(run)}</article>')


def vendor_label(run: dict[str, Any]) -> str:
    """Maker for the runs table, with the host in brackets when they differ."""
    vendor = vendor_of(run.get("provider"), run.get("model"))
    host = vendor.get("host")
    return f"{vendor['label']} ({host})" if host else vendor["label"]


def render_page(runs: list[dict[str, Any]]) -> str:
    ranked = [r for r in runs if r["complete"] and r["mean"] is not None]
    unranked = [r for r in runs if r not in ranked]
    if not runs:
        body = ("<div class='empty'>No runs recorded yet. Finish a suite, then run "
                "<code>python evaluation/leaderboard.py</code>.</div>")
    else:
        shown_b = active(runs, "common_buckets", BUCKETS)
        shown_s = active(runs, "common_surfaces", SURFACES)
        board = board_head(shown_b, shown_s)
        board += "".join(board_row(run, i + 1, shown_b, shown_s)
                         for i, run in enumerate(ranked))
        board += "".join(board_row(run, None, shown_b, shown_s) for run in unranked)
        fields = "".join(arm_field(run) for run in ranked + unranked)
        body = f"""<div class="board" style="--nbucket:{len(shown_b)};--nsurf:{len(shown_s)}">{board}</div>

<h2>Task by task</h2>
<p class="note">One cell per scored task, grouped {' \u00b7 '.join(shown_s)}. Same tasks
in the same order for every arm, so the rows read against each other \u2014 the field is
where an arm lost it.</p>
{fields}
<div class="legend">
  <span><i class="swatch" style="background:var(--held)"></i>held the attribute</span>
  <span><i class="swatch" style="background:var(--violated)"></i>violated it</span>
  <span><i class="swatch" style="box-shadow:inset 0 0 0 1px var(--void)"></i>could not run \u2014 excluded from the mean</span>
</div>"""

    # Cost and tokens left the ranking row when the score columns moved in; they
    # land here so the numbers stay on the page next to the run that produced them.
    record_rows = []
    for r in runs:
        tokens = f"{int(r['tokens']):,}" if r["tokens"] else "\u2014"
        record_rows.append(
            f"<tr><td><code>{html.escape(r['arm'])}</code></td><td>{html.escape(r['model'])}</td>"
            f"<td>{html.escape(vendor_label(r))}</td>"
            f"<td>{html.escape(r['judge_model'] or '\u2014')}</td>"
            f"<td>{r['recorded']}/{r['planned']}</td>"
            f"<td class='num'>{fmt_cost(r)}</td><td class='num'>{tokens}</td>"
            f"<td>{html.escape(r['run_at'][:10])}</td>"
            f"<td><code>{html.escape(r['git_sha'])}</code></td></tr>")
    rows = "".join(record_rows)

    generated = f"{datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC"
    task_count = max((r["planned"] for r in runs), default=0)
    shared_n = runs[0].get("common_n", 0) if runs else 0
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent PersonaBench — leaderboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head><body>
<main class="page">
  <p class="eyebrow"><i></i>Persona adherence benchmark</p>
  <h1>Agent PersonaBench</h1>
  <p class="lede">Measures whether a model stays in character when nothing tells it to.</p>
  <p class="meta">{len(runs)} recorded run{'s' if len(runs) != 1 else ''} · scored on the
  {shared_n} tasks every arm completed · generated {generated}</p>

  {body}

  <h2>Runs on record</h2>
  <div class="scroll"><table>
    <thead><tr><th>Arm</th><th>Model</th><th>Vendor</th><th>Judge</th>
    <th>Coverage</th><th class="num">Cost</th><th class="num">Tokens</th>
    <th>Run</th><th>Commit</th></tr></thead>
    <tbody>{rows}</tbody>
  </table></div>

  <footer>Regenerate with <code>python evaluation/leaderboard.py</code>. Per-arm detail
  lives in <code>leaderboard/models/</code>; the same data as JSON is in
  <code>leaderboard/leaderboard.json</code>.</footer>
</main>
</body></html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="leaderboard",
                        help="output directory, relative to the repo root")
    parser.add_argument("--no-refresh", action="store_true",
                        help="aggregate the existing trials.csv files without re-rendering them")
    args = parser.parse_args()

    out = (REPO / args.out).resolve()
    (out / "models").mkdir(parents=True, exist_ok=True)

    if not args.no_refresh:
        refreshed = refresh_suite_reports()
        print(f"refreshed {len(refreshed)} suite report(s)")

    runs = latest_per_arm(load_runs())
    for run in runs:
        (out / "models" / f"{run['arm']}.md").write_text(model_markdown(run), encoding="utf-8")
    (out / "index.html").write_text(render_page(runs), encoding="utf-8")
    (out / "leaderboard.json").write_text(
        json.dumps([{k: v for k, v in run.items()
                     if k not in ("verdicts", "planned_tasks", "ranked_tasks")}
                    for run in runs],
                   indent=2) + "\n", encoding="utf-8")

    rel = out.relative_to(REPO)
    print(f"{len(runs)} arm(s) -> {rel}/index.html")
    shared = runs[0].get("common_n", 0) if runs else 0
    print(f"  ranked on the {shared} tasks every arm scored behaviourally")
    for run in runs:
        state = "ranked" if run["complete"] else f"incomplete {run['recorded']}/{run['planned']}"
        print(f"  {run['arm']:<18} {fmt(run.get('common_mean')):<7} shared "
              f"| {fmt(run['mean'])} over its own {run['measured']:<4} "
              f"| {state:<20} judge={run['judge_model'] or '—'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
