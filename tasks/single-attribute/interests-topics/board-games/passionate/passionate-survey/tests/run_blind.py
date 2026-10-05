"""Opt-in, fixed-count persona-omitted text controls; calls a real model.

The exact instruction and questionnaire are concatenated without rewriting or
reordering options. Literal JSON transport is preserved and every extracted
submission is scored by the production verifier. No preference is inferred.
This is a text control, NOT a Harbor acting-agent E2E run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone

TASK = Path(__file__).resolve().parents[1]
REPO = next(parent for parent in TASK.parents if (parent / "evaluation/src/llm_client.py").is_file())


def build_prompt(task=TASK):
    # These bytes and order are part of the control contract.
    return ((task / "instruction.md").read_text(encoding="utf-8")
            + "\n\n" + (task / "input/questionnaire.yaml").read_text(encoding="utf-8"))


def source_hashes():
    paths = ["instruction.md", "input/questionnaire.yaml", "persona.yaml", "task.toml",
             "solution/solve.sh", "tests/verifier.py", "tests/answer_key.yaml", "tests/check.json",
             "tests/run_blind.py"]
    return {path: hashlib.sha256((TASK / path).read_bytes()).hexdigest() for path in paths}


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError("duplicate JSON key")
        obj[key] = value
    return obj


def extract_submission(text):
    """Transport literal JSON; never infer, select by score, or repair choices.

    Explanations and JSON fences are not part of an on-disk JSON file. Identical
    repeated objects are harmless transport redundancy; conflicting objects,
    broken framing, arrays and duplicate keys are rejected.
    """
    if not isinstance(text, str) or len(text.encode("utf-8")) > 65536:
        raise ValueError("reply must be bounded UTF-8 text")
    decoder = json.JSONDecoder(object_pairs_hook=unique_object)
    objects = []
    if "```" in text:
        pattern = r"```(?:json)?\s*\n?(.*?)```"
        matches = list(re.finditer(pattern, text, re.DOTALL))
        remainder = re.sub(pattern, "", text, flags=re.DOTALL)
        if not matches or "```" in remainder or any(c in remainder for c in "{}[]"):
            raise ValueError("ambiguous JSON fence or additional JSON outside it")
        for match in matches:
            objects.append(json.loads(match.group(1).strip(), object_pairs_hook=unique_object))
    else:
        remaining = text
        while "{" in remaining:
            start = remaining.index("{")
            if any(c in remaining[:start] for c in "}[]"):
                raise ValueError("invalid surrounding JSON structure")
            value, end = decoder.raw_decode(remaining[start:])
            objects.append(value)
            remaining = remaining[start + end:]
        if any(c in remaining for c in "}[]"):
            raise ValueError("unbalanced surrounding JSON structure")
    if not objects or any(not isinstance(obj, dict) for obj in objects):
        raise ValueError("expected a literal JSON object")
    if any(obj != objects[0] for obj in objects[1:]):
        raise ValueError("multiple contradictory JSON objects")
    return objects[0], len(objects)


def score_reply(directory, text):
    (directory / "survey_result.json").write_text(text, encoding="utf-8")
    result = directory / "verifier"
    env = {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8",
           "ADHERENCE_OUTPUT_DIR": str(directory), "ADHERENCE_VERIFIER_DIR": str(result)}
    completed = subprocess.run([sys.executable, str(TASK / "tests/verifier.py")],
                               env=env, text=True, capture_output=True, timeout=30)
    (directory / "verifier_stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (directory / "verifier_stderr.txt").write_text(completed.stderr, encoding="utf-8")
    scored = json.loads((result / "structured_output.json").read_text())
    if completed.returncode not in (0, 1) or "Traceback" in completed.stderr:
        raise RuntimeError("production verifier failed instead of returning a verdict")
    return scored


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="opus-4-8", help="configured arm id")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--runs", type=int, default=3)
    args = parser.parse_args()
    if args.runs < 3:
        parser.error("text controls require at least three preregistered runs")
    output = args.output.resolve()
    if output.exists() and any(output.iterdir()):
        parser.error("output must be new or empty; prior results are never overwritten")
    if output == TASK or TASK in output.parents:
        parser.error("generated evidence must be outside the task leaf")
    output.mkdir(parents=True, exist_ok=True)
    config = json.loads((REPO / "evaluation/configs" / (args.model + ".json")).read_text())
    os.environ.update(LLM_PROVIDER=config["provider"], LLM_MODEL=config["model"],
                      LLM_REASONING_EFFORT=args.effort, LLM_CALL_ROLE="arm")
    sys.path.insert(0, str(REPO / "evaluation/src"))
    from llm_client import chat
    import usage
    prompt = build_prompt()
    (output / "actor_prompt.txt").write_text(prompt, encoding="utf-8")
    metadata = {
        "kind": "persona-blind-text-control", "persona_used": False,
        "surface": "survey", "arm": args.model, "provider": config["provider"],
        "model_id": config["model"], "effort": args.effort, "runs_planned": args.runs,
        "max_tokens_requested": 2000,
        "temperature_requested": config.get("temperature", 0.0),
        "provider_seed_guaranteed": False,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "source_sha256": source_hashes(),
        "independent_uniform_pass_probability": 1 / 256,
        "coherent_uniform_category_pass_probability": 1 / 4,
        "caveat": "Small fixed sample; single-turn text controls, not Harbor E2E; no provider seed guarantee.",
        "records": [],
    }
    (output / "control_summary.json").write_text(json.dumps(metadata, indent=2))
    for index in range(1, args.runs + 1):
        directory = output / f"run-{index:03d}"
        directory.mkdir()
        usage.reset()
        try:
            reply = chat([{"role": "user", "content": prompt}], model=config["model"],
                         max_tokens=2000, temperature=config.get("temperature", 0.0))
            (directory / "raw_reply.txt").write_text(reply, encoding="utf-8")
            transport_error = None
            copies = 0
            try:
                document, copies = extract_submission(reply)
                payload = json.dumps(document, ensure_ascii=False)
            except (ValueError, RecursionError) as exc:
                transport_error = str(exc)
                payload = reply
            scored = score_reply(directory, payload)
            record = {"run": index, "status": "completed", "verdict": scored["verdict"],
                      "reward": scored["reward"], "selected_answers": scored.get("selected_answers"),
                      "reason": scored.get("reason"), "usage": usage.summary(),
                      "literal_json_copies": copies, "transport_error": transport_error,
                      "valid_complete_choice_set": transport_error is None
                          and scored.get("total_questions") == 4
                          and len(scored.get("selected_answers", {})) == 4}
        except Exception as exc:
            # Record all infrastructure failures, without credential-bearing diagnostics.
            record = {"run": index, "status": "error", "error_type": type(exc).__name__,
                      "usage": usage.summary()}
        metadata["records"].append(record)
        metadata["responded"] = sum(r["status"] == "completed" for r in metadata["records"])
        metadata["completed"] = sum(r.get("valid_complete_choice_set", False) for r in metadata["records"])
        metadata["passes"] = sum(r.get("verdict") == "HELD" for r in metadata["records"])
        (output / "control_summary.json").write_text(json.dumps(metadata, indent=2))
        print(json.dumps(record), flush=True)
    metadata["finished_utc"] = datetime.now(timezone.utc).isoformat()
    metadata["source_unchanged"] = metadata["source_sha256"] == source_hashes()
    (output / "control_summary.json").write_text(json.dumps(metadata, indent=2))
    if not metadata["source_unchanged"]:
        raise SystemExit("task changed while control batch was running")
    if metadata["responded"] != args.runs:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
