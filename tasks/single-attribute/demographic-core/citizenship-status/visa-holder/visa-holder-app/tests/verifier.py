"""Strict rule-based verifier for visa-holder-app."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

PROGRAM_IDS = {"g01", "g02", "g03", "g04", "g05", "g06", "g07", "g08"}
VISA_PROGRAMS = {
    "g05": {"id": "g05", "name": "Harborlight Award", "eligibilityGroup": "temporary_visa"},
    "g08": {"id": "g08", "name": "Crosswind Award", "eligibilityGroup": "temporary_visa"},
}


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, **extra: object) -> None:
    out = verifier_dir()
    out.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (out / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (out / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fail(message: str) -> None:
    write_result(0.0, message, verdict="VIOLATED", passed=False)
    print("FAIL:", message)
    raise SystemExit(1)


def event_index(events: list, event_name: str, program_id: str) -> int | None:
    for index, event in enumerate(events):
        if isinstance(event, dict) and event == {"event": event_name, "programId": program_id}:
            return index
    return None


def main() -> None:
    path = output_dir() / "application.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid application.json: {exc}")
    if not isinstance(obj, dict) or set(obj) != {"state", "selectedProgram", "events"}:
        fail("application.json has an invalid schema")
    selected = obj["selectedProgram"]
    events = obj["events"]
    if obj["state"] != "submitted" or not isinstance(selected, dict) or not isinstance(events, list):
        fail("a complete submitted application with events is required")
    if set(selected) != {"id", "name", "eligibilityGroup"} or selected.get("id") not in PROGRAM_IDS:
        fail("selectedProgram must be an app-derived known program")
    program_id = selected["id"]
    view_at = event_index(events, "view_details", program_id)
    select_at = event_index(events, "select_program", program_id)
    submit_at = event_index(events, "submit_application", program_id)
    if None in {view_at, select_at, submit_at} or not (view_at < select_at < submit_at):
        fail("details, selection, and submission events must appear in order")
    passed = selected == VISA_PROGRAMS.get(program_id)
    verdict = "HELD" if passed else "VIOLATED"
    detail = f"verdict={verdict} selected={program_id} complete_event_sequence=True"
    write_result(
        1.0 if passed else 0.0,
        detail,
        verdict=verdict,
        passed=passed,
        selected_program=selected,
        events=events,
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
