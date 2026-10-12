"""Recover actual completed v1 observer events; retain original failed trial."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import zipfile

TASK = Path(__file__).resolve().parents[1]


def write(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def recover(trial: Path) -> Path:
    metadata = json.loads((trial / "diagnostic-metadata.json").read_text(encoding="utf-8"))
    if metadata.get("status") != "error" or metadata.get("error_type") != "AttributeError":
        raise ValueError("recovery is limited to the recorded v1 observer failure")
    if not metadata.get("persona_block_matches_treatment") or not metadata.get("native_persona_unchanged"):
        raise ValueError("missing verified persona treatment or native source consistency")
    for name in ("tests/rubric.md", "persona.yaml"):
        if hashlib.sha256((TASK / name).read_bytes()).hexdigest() != metadata["source_sha256"][name]:
            raise ValueError(f"frozen scoring source changed: {name}")
    locked_verifier = metadata["source_sha256"]["tests/verifier.py"]
    verifier_evidence = next(
        (candidate for candidate in (TASK / "tests/verifier.py", trial / "verifier-v1.py")
         if candidate.is_file() and hashlib.sha256(candidate.read_bytes()).hexdigest() == locked_verifier),
        None,
    )
    if verifier_evidence is None:
        raise ValueError("neither current nor archived verifier matches the original source lock")
    raw_events = (trial / "harness-events.json").read_bytes()
    events = json.loads(raw_events)
    turns = [item["turn"] for item in events if item.get("type") == "turn"]
    assistant_events = [item for item in events if item.get("type") == "assistant_message"]
    if [t.get("turnIndex") for t in turns] != list(range(1, 13)) or len(assistant_events) != 12:
        raise ValueError("recovery requires exactly 12 ordered completed real exchanges")
    transcript = []
    for turn, event in zip(turns, assistant_events):
        if any(turn[key] != event[key] for key in ("turnIndex", "userMessage", "assistantMessage")):
            raise ValueError("completed turn and live assistant event disagree")
        transcript.extend([{"role": "user", "content": turn["userMessage"]},
                           {"role": "assistant", "content": turn["assistantMessage"]}])
    out = trial / "recovered-diagnostic"
    if out.exists():
        raise ValueError("recovered output exists; refusing to overwrite")
    out.mkdir()
    import yaml
    persona_id = yaml.safe_load((TASK / "persona.yaml").read_text(encoding="utf-8"))["persona_id"]
    write(out / "transcript.json", transcript)
    write(out / "user_turns.json", {"persona": persona_id,
                                    "turns": [t["userMessage"] for t in turns]})
    usage = metadata["partial_actor_usage"]
    write(out / "generation.json", {
        "model": metadata["model"], "provider": metadata["provider"],
        "condition": metadata["condition"], "full_transcript": transcript,
        "token_usage": usage["summary"], "calls": usage["calls"],
        "recovered_from": "../harness-events.json", "diagnostic_only": True,
        "original_trial_status": "error",
    })
    write(out / "recovery.json", {
        "diagnostic_only": True, "original_trial_status": "error",
        "reason": "Complete real exchanges survived task-local observer's final serialization failure.",
        "harness_events_sha256": hashlib.sha256(raw_events).hexdigest(),
        "metadata_sha256": hashlib.sha256((trial / "diagnostic-metadata.json").read_bytes()).hexdigest(),
        "recovery_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "model_calls_repeated": 0, "turns_preserved_verbatim": 12,
        "original_verifier_sha256": locked_verifier,
    })
    with zipfile.ZipFile(out / "trace.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in ("transcript.json", "user_turns.json", "generation.json", "recovery.json"):
            bundle.write(out / name, name)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial", type=Path, required=True)
    parser.add_argument("--judge", action="store_true", help="Invokes the original trial's named model as judge.")
    args = parser.parse_args()
    out = recover(args.trial)
    if not args.judge:
        return 0
    metadata = json.loads((args.trial / "diagnostic-metadata.json").read_text(encoding="utf-8"))
    os.environ.update({"ADHERENCE_OUTPUT_DIR": str(out.resolve()),
                       "ADHERENCE_VERIFIER_DIR": str(out.resolve()),
                       "ADHERENCE_JUDGE_MODEL": metadata["model"],
                       "ADHERENCE_JUDGE_PROVIDER": metadata["provider"],
                       "LLM_CALL_ROLE": "judge"})
    spec = importlib.util.spec_from_file_location("chat_recovery_verifier", TASK / "tests" / "verifier.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.main()


if __name__ == "__main__":
    raise SystemExit(main())
