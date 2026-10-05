"""Freeze eight authored semantic checks, then explicitly run each once."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
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
import verifier

MODEL = "claude-haiku-4-5-20251001"
LEAVES = ("interactive-debugger/debugger-first-chat", "instrumentation/instrumentation-first-chat")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def requests_for(check, rubric):
    """Capture the real production request builder without making any calls."""
    require_legacy_construct()
    requests = {}
    def record(stage, system, payload):
        requests[stage] = {"system": system, "payload": payload}
        return "HELD"
    verifier.assess(check["turns"], check["target"], record, rubric)
    return requests[check["stage"]]


def freeze(out, matrix_revision=2):
    require_legacy_construct()
    if out.exists():
        raise ValueError("refusing to overwrite the prospective schedule")
    out.mkdir(parents=True)
    matrix_name = "semantic_checks.json" if matrix_revision == 1 else "semantic_checks_v2.json"
    matrix = json.loads((TASK / "tests" / matrix_name).read_text(encoding="utf-8"))
    rubric = (TASK / "tests/rubric.md").read_text(encoding="utf-8")
    if len(matrix["checks"]) != 8 or len({c["id"] for c in matrix["checks"]}) != 8:
        raise ValueError("the authorized matrix requires exactly eight unique checks")
    sources = {}
    with zipfile.ZipFile(out / "prospective-source.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for leaf in LEAVES:
            for path in sorted((BASE / leaf).rglob("*")):
                if path.is_file() and "__pycache__" not in path.parts:
                    name = path.relative_to(REPO).as_posix()
                    archive.write(path, name)
                    sources[name] = digest(path.read_bytes())
        for path in sorted((REPO / "evaluation/src").rglob("*.py")):
            name = path.relative_to(REPO).as_posix()
            archive.write(path, name)
            sources[name] = digest(path.read_bytes())
        guidelines = REPO / "evaluation/src/playground/user_sim/sim_guidelines.md"
        name = guidelines.relative_to(REPO).as_posix()
        archive.write(guidelines, name)
        sources[name] = digest(guidelines.read_bytes())
    schedule = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": MODEL, "judge_provider": "anthropic", "rubric_revision": verifier.RUBRIC_REVISION,
        "rubric_sha256": digest(rubric.encode()), "judge_protocol_revision": 2,
        "prompt_assembly_revision": verifier.PROMPT_ASSEMBLY_REVISION,
        "judge_limit": 8, "matrix": matrix,
        "requests": {c["id"]: requests_for(c, rubric) for c in matrix["checks"]},
        "actor_gate": "All eight strict verdicts must match the predeclared gold labels; otherwise pause for root assessment.",
        "actors": [{"leaf": LEAVES[0], "condition": "full"},
                   {"leaf": LEAVES[1], "condition": "full"},
                   {"leaf": LEAVES[0], "condition": "blind"}],
        "actor_limit": 3, "max_persona_turns": 12, "force_full_turns": True,
        "persona_max_tokens": 4096, "persona_temperature": 0.7,
        "bot_max_tokens": 1024, "bot_temperature": 0.6,
        "judge_max_tokens": 128, "judge_temperature": "provider default (unchanged forced-tool protocol)",
        "actor_driver_revision": 2, "arm_label": "opus-4-8",
        "seed": "No deterministic seed support in unchanged shared harness",
        "remaining_settings": "Unchanged shared harness, finite send-message exchanges, shared self-report and default retry limits; no capability configuration file",
        "sources": sources,
    }
    write(out / "schedule.json", schedule)
    return schedule


def execute(out):
    require_legacy_construct()
    schedule = json.loads((out / "schedule.json").read_text(encoding="utf-8"))
    if (out / "judge-checks.json").exists():
        raise ValueError("refusing to repeat or overwrite model checks")
    for name, expected in schedule["sources"].items():
        if digest((REPO / name).read_bytes()) != expected:
            raise ValueError("source changed after the prospective freeze: " + name)
    os.environ.update({"ADHERENCE_JUDGE_MODEL": MODEL, "ADHERENCE_JUDGE_PROVIDER": "anthropic",
                       "LLM_CALL_ROLE": "judge"})
    import judge
    import judge_protocol
    import usage
    resolved = judge.resolve()
    if resolved.model != MODEL or resolved.provider != "anthropic":
        raise ValueError("judge does not match the authorized model")
    usage.reset()
    record = {"status": "started", "schedule_sha256": digest((out / "schedule.json").read_bytes()),
              "judge": resolved._asdict(), "checks": [], "actor_calls": 0}
    write(out / "judge-checks.json", record)
    for check in schedule["matrix"]["checks"]:
        request = schedule["requests"][check["id"]]
        item = {"id": check["id"], "stage": check["stage"], "expected": check["expected"],
                "model": resolved.model, "provider": resolved.provider,
                "system_prompt": request["system"], "payload": request["payload"], "raw": None}
        record["checks"].append(item)
        start = len(usage.CALL_LOG)
        try:
            item["actual"] = verifier.parse_verdict(judge_protocol.call_judge(
                resolved, request["system"], request["payload"], item))
            item["matches_gold"] = item["actual"] == check["expected"]
        except Exception as exc:
            item["error_type"] = type(exc).__name__
            item["matches_gold"] = False
        finally:
            item["usage"] = list(usage.CALL_LOG[start:])
            item["system_sha256"] = digest(item["system_prompt"].encode())
            item["payload_sha256"] = digest(item["payload"].encode())
            record["usage"] = usage.summary()
            write(out / "judge-checks.json", record)
    record["status"] = "passed" if all(c["matches_gold"] for c in record["checks"]) else "failed"
    write(out / "judge-checks.json", record)
    return record


def require_legacy_construct():
    if getattr(verifier, "CONSTRUCT_VERSION", 2) != 2:
        raise ValueError("Historical construct-2 helper; use its archived source with old artifacts. Construct 3 uses completion_checks.py.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--execute", action="store_true", help="Run the already frozen eight checks once; paid calls.")
    parser.add_argument("--matrix-revision", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    if args.execute:
        result = execute(args.output)
        print(json.dumps({"status": result["status"], "checks": len(result["checks"]), "usage": result["usage"]}))
        return 0 if result["status"] == "passed" else 3
    freeze(args.output, args.matrix_revision)
    print("Prospective schedule and sources frozen; no model calls made.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
