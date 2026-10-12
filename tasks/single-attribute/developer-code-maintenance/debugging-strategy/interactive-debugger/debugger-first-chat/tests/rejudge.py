"""Explicit posthoc judging of a saved diagnostic dialogue; no actor rerun."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

TASK = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TASK / "tests"))
import verifier


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", required=True)
    parser.add_argument("--input", "--recovered", dest="input_dir", type=Path, required=True,
                        help="Saved diagnostic directory, or labeled recovered diagnostic.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--target", choices=verifier.TARGETS)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("refusing to overwrite an earlier judgment")
    metadata_path = args.input_dir / "diagnostic-metadata.json"
    if (args.input_dir / "recovery.json").is_file():
        metadata_path = args.input_dir.parent / "diagnostic-metadata.json"
    if not metadata_path.is_file():
        parser.error("expected saved diagnostic metadata or labeled recovered input")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    rubric = (TASK / "tests/rubric.md").read_text(encoding="utf-8")
    if hashlib.sha256(rubric.encode()).hexdigest() != metadata["source_sha256"]["tests/rubric.md"]:
        parser.error("semantic rubric changed from the actor-trial lock")
    import yaml
    persona_id = yaml.safe_load((TASK / "persona.yaml").read_text(encoding="utf-8"))["persona_id"]
    turns = verifier.validate_artifacts(args.input_dir, persona_id)
    target = args.target or yaml.safe_load((TASK / "persona.yaml").read_text(encoding="utf-8"))["attributes"]["debugging_strategy"]["value"]
    repo = TASK
    while repo != repo.parent and not (repo / "evaluation/src").is_dir():
        repo = repo.parent
    sys.path.insert(0, str(repo / "evaluation/src"))
    import judge
    os.environ.update({"ADHERENCE_JUDGE_MODEL": args.model_id,
                       "ADHERENCE_JUDGE_PROVIDER": judge.infer_provider(args.model_id),
                       "LLM_CALL_ROLE": "judge"})
    import judge_protocol
    import usage
    resolved = judge.resolve()
    calls = []
    detail = {
        "verdict": "ERROR", "reward": 0.0, "posthoc_rejudge": True,
        "input_is_recovered": (args.input_dir / "recovery.json").is_file(),
        "actor_calls_repeated": 0, "original_trial_status": metadata["status"],
        "original_condition": metadata["condition"], "original_persona": persona_id,
        "judge_protocol_revision": judge_protocol.REVISION,
        "rubric_revision": verifier.RUBRIC_REVISION,
        "rubric_sha256": hashlib.sha256(rubric.encode()).hexdigest(),
        "verifier_sha256": hashlib.sha256((TASK / "tests/verifier.py").read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256((TASK / "tests/judge_protocol.py").read_bytes()).hexdigest(),
        "transcript_sha256": hashlib.sha256((args.input_dir / "transcript.json").read_bytes()).hexdigest(),
        "judge": resolved._asdict(), "judge_calls": calls,
    }
    def call(stage, system, payload):
        start = len(usage.CALL_LOG)
        item = {"stage": stage, "system_prompt": system, "model": resolved.model,
                "provider": resolved.provider, "raw": None}
        calls.append(item)
        try:
            try:
                return judge_protocol.call_judge(resolved, system, payload, item)
            except ValueError as exc:
                raise verifier.JudgeError(str(exc)) from exc
        finally:
            item["usage"] = list(usage.CALL_LOG[start:])
    usage.reset()
    try:
        detail.update(verifier.assess(turns, target, call, rubric))
    except verifier.JudgeError as exc:
        detail.update(error="judge_parse_error", detail=str(exc))
    except Exception as exc:
        detail.update(error="verifier_dependency_or_judge_error", detail=type(exc).__name__)
    detail["judge_usage"] = usage.summary()
    verifier.write_result(args.output, target, detail)
    print(json.dumps({key: detail.get(key) for key in
                      ("verdict", "complete", "target_count", "error", "judge_usage")}))
    return 3 if detail.get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
