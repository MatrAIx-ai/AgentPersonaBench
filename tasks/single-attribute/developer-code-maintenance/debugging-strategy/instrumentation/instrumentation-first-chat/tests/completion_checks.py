"""Archived protocol-3.1 calibration; execution is disabled for current protocols."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import platform
from pathlib import Path
import sys
import zipfile

TASK = Path(__file__).resolve().parents[1]
BASE = TASK.parents[1]
REPO = TASK
while REPO != REPO.parent and not (REPO / "evaluation/src").is_dir():
    REPO = REPO.parent
sys.path.insert(0, str(TASK / "tests"))
sys.path.insert(0, str(REPO / "evaluation/src"))
import completion_protocol
import verifier

MODEL = "claude-haiku-4-5-20251001"
LEAVES = ("interactive-debugger/debugger-first-chat", "instrumentation/instrumentation-first-chat")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, data):
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))


def expand_cases(matrix):
    if matrix.get("construct_version") != 3 or matrix.get("status") != "independently reviewed; frozen before model calls":
        raise ValueError("completion fixtures have not passed independent review")
    base = matrix["base_turns"]
    cases = matrix["cases"]
    if not isinstance(base, list) or len(base) != 12 or not all(isinstance(t, str) and t.strip() for t in base):
        raise ValueError("fixtures need a twelve-turn persona context")
    if not isinstance(cases, list) or len(cases) != 12 or len({c["id"] for c in cases}) != 12:
        raise ValueError("exactly twelve distinct fixtures are authorized")
    expanded = []
    for case in cases:
        if case["incident"] not in completion_protocol.FINAL_TURNS or case["expected"] not in ("COMPLETE", "INCOMPLETE", "UNRESOLVED"):
            raise ValueError("unknown fixture incident or gold status")
        turns = list(base)
        for key, text in case["overrides"].items():
            if not isinstance(key, str) or not key.isdigit() or not 1 <= int(key) <= 12:
                raise ValueError("invalid fixture override turn")
            if not isinstance(text, str) or not text.strip() or len(text) > verifier.MAX_MESSAGE:
                raise ValueError("invalid fixture override content")
            turns[int(key) - 1] = text
        system, payload = verifier.completion_request(turns, case["incident"])
        expanded.append({**case, "turns": turns, "system_prompt": system, "payload": payload})
    return expanded


def continuation_plan(previous, cases):
    """A single rejected request may leave eleven never-run calibration cases."""
    old_schedule = json.loads((previous / "schedule.json").read_text(encoding="utf-8"))
    old = json.loads((previous / "execution.json").read_text(encoding="utf-8"))
    if old.get("status") != "failed" or old.get("attempted_calls") != 1 or len(old.get("checks", [])) != 1:
        raise ValueError("continuation requires exactly one preserved failed request")
    first = old["checks"][0]
    if first.get("error_type") != "BadRequestError" or first.get("raw") is not None or "validated_report" in first:
        raise ValueError("a semantic result or another failure cannot use this transport continuation")
    if old_schedule.get("cases") != cases or first.get("id") != cases[0]["id"]:
        raise ValueError("continuation may not change the reviewed cases, golds, or semantic prompts")
    return cases[1:], {
        "previous_schedule_sha256": digest((previous / "schedule.json").read_bytes()),
        "previous_execution_sha256": digest((previous / "execution.json").read_bytes()),
        "prior_attempted_calls": 1, "total_request_limit": 12,
        "unjudged_case": cases[0]["id"],
        "original_twelve_case_gate_satisfied": False,
        "gate_amendment": "Lead approved before calls: if all eleven never-run cases and host/schema checks pass, the three scheduled actors may run as limited exploratory coverage. This does not satisfy or replace the original 12/12 calibration claim.",
    }


def freeze(output, continuation=None):
    if completion_protocol.REVISION != "3.1":
        raise ValueError("This archived single-judge driver cannot validate the current protocol; use criteria_checks.py")
    if output.exists():
        raise ValueError("refusing to overwrite an earlier calibration")
    matrix = json.loads((TASK / "tests/completion_cases.json").read_text(encoding="utf-8"))
    cases = expand_cases(matrix)
    continuation_info = None
    if continuation is not None:
        cases, continuation_info = continuation_plan(continuation, cases)
    output.mkdir(parents=True)
    sources = {}
    with zipfile.ZipFile(output / "source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        paths = []
        for leaf in LEAVES:
            paths.extend(p for p in (BASE / leaf).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
        paths.extend((REPO / "evaluation/src").rglob("*.py"))
        paths.append(REPO / "evaluation/src/playground/user_sim/sim_guidelines.md")
        for path in sorted(paths):
            name = path.relative_to(REPO).as_posix()
            sources[name] = digest(path.read_bytes())
            archive.write(path, name)
    import anthropic
    import yaml
    schedule = {
        "frozen_utc": datetime.now(timezone.utc).isoformat(), "construct_version": 3,
        "model": MODEL, "provider": "anthropic", "calibration_limit": len(cases),
        "judge_protocol_revision": completion_protocol.REVISION,
        "prior_attempted_calls": 1 if continuation_info else 0,
        "total_request_limit": 12, "continuation": continuation_info,
        "runtime": {"python": platform.python_version(), "anthropic": anthropic.__version__, "yaml": yaml.__version__},
        "cases": cases, "matrix": matrix, "sources": sources,
        "stop_rule": "Stop paid calls immediately on any protocol, citation, or expected-status mismatch; no tuning or retry.",
        "actor_gate": (continuation_info["gate_amendment"] if continuation_info else
                       "All twelve independently reviewed cases must pass, with unchanged frozen sources."),
        "actors": [{"leaf": LEAVES[0], "condition": "full", "seed_label": 47, "runner": "standard Linux"},
                   {"leaf": LEAVES[1], "condition": "full", "seed_label": 48, "runner": "standard Linux"},
                   {"leaf": LEAVES[0], "condition": "blind", "seed_label": 49, "runner": "explicit Linux diagnostic"}],
        "actor_limit": 3, "max_judgments_per_actor": 6,
        "max_persona_turns": 12, "force_full_turns": True,
        "persona_max_tokens": 4096, "persona_temperature": 0.7,
        "persona_temperature_forwarding": "separate shared tool_client conditional; source archived",
        "generated_colleague_calls": 5, "colleague_max_tokens": 1024, "colleague_temperature": 0.6,
        "colleague_temperature_forwarded": False,
        "completion_max_tokens": 1024, "method_max_tokens": 128,
        "judge_temperature": "provider default", "judge_timeout_seconds": 60, "judge_retries": 0,
        "verifier_timeout_seconds": 420,
        "seed": "The unchanged simulator does not expose a deterministic sampling seed.",
        "shared_behavior": "Unchanged full native renderer, simulator guidelines, tool definitions, self-report and finite-turn handling.",
    }
    write(output / "schedule.json", schedule)
    return schedule


def verify_sources(schedule):
    for name, expected in schedule["sources"].items():
        if digest((REPO / name).read_bytes()) != expected:
            raise ValueError("source changed after freeze: " + name)


def execute(output):
    schedule = json.loads((output / "schedule.json").read_text(encoding="utf-8"))
    verify_sources(schedule)
    if (output / "execution.json").exists():
        raise ValueError("refusing to repeat calibration calls or overwrite evidence")
    count = len(schedule["cases"])
    prior = schedule.get("prior_attempted_calls", 0)
    if count != schedule.get("calibration_limit", count) or not 1 <= count <= 12 or prior + count > 12:
        raise ValueError("calibration exceeds its frozen cumulative request budget")
    if completion_protocol.REVISION != "3.1":
        raise ValueError("This archived single-judge driver cannot validate the current protocol; use criteria_checks.py")
    os.environ.update({"ADHERENCE_JUDGE_MODEL": MODEL, "ADHERENCE_JUDGE_PROVIDER": "anthropic",
                       "LLM_CALL_ROLE": "judge"})
    import judge
    import judge_protocol
    import usage
    resolved = judge.resolve()
    if resolved.model != MODEL or resolved.provider != "anthropic":
        raise ValueError("resolved judge is not the authorized Haiku model")
    usage.reset()
    record = {"status": "started", "schedule_sha256": digest((output / "schedule.json").read_bytes()),
              "judge": resolved._asdict(), "checks": [], "actor_calls": 0, "attempted_calls": 0,
              "prior_attempted_calls": prior, "current_request_limit": count,
              "continuation": schedule.get("continuation")}
    write(output / "execution.json", record)
    for case in schedule["cases"]:
        item = {"id": case["id"], "stage": "completion/" + case["incident"],
                "expected": case["expected"], "model": resolved.model, "provider": resolved.provider,
                "system_prompt": case["system_prompt"], "payload": case["payload"], "raw": None}
        record["checks"].append(item)
        record["attempted_calls"] += 1
        start = len(usage.CALL_LOG)
        try:
            raw = judge_protocol.call_judge(resolved, case["system_prompt"], case["payload"], item)
            report = completion_protocol.validate_report(raw, case["incident"], case["turns"])
            item["validated_report"] = report
            item["matches_gold"] = report["status"] == case["expected"]
        except Exception as exc:
            item["error_type"] = type(exc).__name__
            item["matches_gold"] = False
        finally:
            item["usage"] = list(usage.CALL_LOG[start:])
            item["system_sha256"] = digest(item["system_prompt"].encode("utf-8"))
            item["payload_sha256"] = digest(item["payload"].encode("utf-8"))
            record["usage"] = usage.summary()
            write(output / "execution.json", record)
        if not item["matches_gold"]:
            break
    record["status"] = "passed" if len(record["checks"]) == count and all(c["matches_gold"] for c in record["checks"]) else "failed"
    record["cumulative_attempted_calls"] = prior + record["attempted_calls"]
    record["unrun_cases"] = [c["id"] for c in schedule["cases"][len(record["checks"]):]]
    write(output / "execution.json", record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="Invoke the authorized Haiku judge for the already frozen cases.")
    parser.add_argument("--continuation-from", type=Path,
                        help="Freeze the eleven never-run cases after the preserved first-request schema rejection.")
    args = parser.parse_args()
    if args.execute:
        if args.continuation_from is not None:
            parser.error("--continuation-from is a freeze-only option")
        record = execute(args.output)
        print(json.dumps({key: record[key] for key in ("status", "attempted_calls", "usage", "unrun_cases")}))
        return 0 if record["status"] == "passed" else 3
    schedule = freeze(args.output, args.continuation_from)
    print(f"{len(schedule['cases'])}-case schedule, settings and sources frozen; no model calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
