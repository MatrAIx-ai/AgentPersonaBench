#!/usr/bin/env python3
"""Rule verifier for the Harefield Press Studio app artifact.

Ground truth is tests/answer_key.yaml, which sits next to this file: tests/ is
the only directory the harness copies into the environment the verifier runs in
(it lands at /tests), and the task's input/ tree is both absent there and
agent-writable on the CUA desktop, so it can never be the source of truth.
Nothing the artifact says about itself is trusted either. The artifact must be
the complete app record: the exact top-level key set, whole option objects equal
to catalog entries, an ordered event trace ending in exactly one submit event
that agrees with the selections, and a select event for every section before
that submit (the last select per section must match the recorded selection, so
changing one's mind before submitting is fine). Verdict: HELD iff every selected
option satisfies adherent_option(); any malformed or incomplete input is ERROR
with reward 0. Every failure is routed through write_result, never a traceback.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

# Next to this file in the repo (tests/) and in the environment (/tests), so the
# same expression resolves in both layouts.
ANSWER_KEY = Path(__file__).resolve().parent / "answer_key.yaml"
ARTIFACT_NAME = "planner_order.json"
SELECTION_KEY = "order"
FACT_KEY = "distinguishable"
TOP_LEVEL_KEYS = {SELECTION_KEY, "events", "completed"}
SELECT_KEYS = {"seq", "type", "group", "optionId"}
SUBMIT_KEYS = {"seq", "type", "optionIds"}
MAX_EVENTS = 200


def adherent_option(option: dict) -> bool:
    """The style marks its states with a symbol, letter, shape or pattern, not by tint alone."""
    return option.get(FACT_KEY) == "multi_cue"


# --- result writing (single path for every outcome) --------------------------
def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR") or "/app/output")


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR") or output_dir())


def write_result(reward: float, verdict: str, detail: str, **extra: object) -> None:
    target = verifier_dir()
    target.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "verdict": verdict, "passed": reward == 1.0, "detail": detail, **extra}
    (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                                   encoding="utf-8")


def fail(message: str) -> None:
    write_result(0.0, "ERROR", message)
    print(f"FAIL: {message}")
    raise SystemExit(1)


# --- ground truth: the host-side answer key shipped inside tests/ ------------
def parse_key(text: str) -> object:
    """The key is a JSON document behind '#' comment lines, so it is valid YAML too."""
    return json.loads("\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#")))


def load_catalog(source: Path = ANSWER_KEY) -> list[dict]:
    """Read the section catalog from the host-side answer key and validate its shape."""
    if not source.is_file():
        raise ValueError(f"missing answer key {source}")
    catalog = parse_key(source.read_text(encoding="utf-8"))
    if not isinstance(catalog, list) or not catalog:
        raise ValueError("the answer key must hold a non-empty list of sections")
    group_ids: set[str] = set()
    option_ids: set[str] = set()
    for group in catalog:
        if (not isinstance(group, dict) or not isinstance(group.get("id"), str) or not group["id"]
                or not isinstance(group.get("title"), str) or not isinstance(group.get("options"), list)
                or not group["options"]):
            raise ValueError("every section needs a string id, a title and a non-empty options list")
        if group["id"] in group_ids:
            raise ValueError(f"duplicate section id {group['id']!r}")
        group_ids.add(group["id"])
        for option in group["options"]:
            if (not isinstance(option, dict) or FACT_KEY not in option
                    or not all(isinstance(option.get(key), str) and option[key] for key in ("id", "name", "detail"))):
                raise ValueError(f"every option in section {group['id']!r} needs string id/name/detail and {FACT_KEY!r}")
            if option["id"] in option_ids:
                raise ValueError(f"duplicate option id {option['id']!r}")
            option_ids.add(option["id"])
    return catalog


def option_index(catalog: list[dict]) -> dict[str, dict[str, dict]]:
    return {group["id"]: {option["id"]: option for option in group["options"]} for group in catalog}


# --- artifact validation ------------------------------------------------------
def load_artifact(path: Path) -> dict:
    if not path.is_file():
        fail(f"missing {path}")
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        fail(f"cannot read {path.name}: {exc}")
    if not raw.strip():
        fail(f"{path.name} is empty")
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError as exc:
        fail(f"{path.name} is not valid JSON: {exc}")
    if not isinstance(obj, dict):
        fail(f"{path.name} must be a JSON object")
    if set(obj) != TOP_LEVEL_KEYS:
        fail(f"{path.name} must contain exactly the keys {sorted(TOP_LEVEL_KEYS)}")
    if obj["completed"] is not True:
        fail("the app did not record a completed submission")
    return obj


def check_selection(catalog: list[dict], selected: object) -> dict[str, str]:
    """Every section chosen exactly once, each choice equal to a catalog entry; returns section -> option id."""
    expected = option_index(catalog)
    if not isinstance(selected, dict):
        fail(f"{SELECTION_KEY} must be an object keyed by section id")
    if set(selected) != set(expected):
        fail(f"{SELECTION_KEY} must contain every section exactly once: {sorted(expected)}")
    chosen: dict[str, str] = {}
    for group_id, options in expected.items():
        choice = selected[group_id]
        if not isinstance(choice, dict) or not isinstance(choice.get("id"), str):
            fail(f"selection for section {group_id!r} must be an option object with a string id")
        if choice["id"] not in options:
            fail(f"unknown option {choice['id']!r} in section {group_id!r}")
        if choice != options[choice["id"]]:
            fail(f"option {choice['id']!r} in section {group_id!r} does not match the app catalog")
        chosen[group_id] = choice["id"]
    return chosen


def check_events(catalog: list[dict], events: object, chosen: dict[str, str]) -> None:
    """Consecutive seq numbers, known ids, exactly one final submit that agrees, a matching select before it."""
    expected = option_index(catalog)
    if not isinstance(events, list) or not events:
        fail("events must be a non-empty list")
    if len(events) > MAX_EVENTS:
        fail(f"events list exceeds {MAX_EVENTS} entries")
    last_select: dict[str, str] = {}
    submits = 0
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or type(event.get("seq")) is not int or event["seq"] != index:
            fail("events must be objects with consecutive seq numbers starting at 1")
        kind = event.get("type")
        if kind == "select":
            if set(event) != SELECT_KEYS:
                fail(f"select event {index} is malformed")
            group_id, option_id = event["group"], event["optionId"]
            if (not isinstance(group_id, str) or not isinstance(option_id, str)
                    or group_id not in expected or option_id not in expected[group_id]):
                fail(f"select event {index} names an unknown section or option")
            if submits:
                fail("a select event follows the submit event")
            last_select[group_id] = option_id
        elif kind == "submit":
            if set(event) != SUBMIT_KEYS:
                fail(f"submit event {index} is malformed")
            submits += 1
            if submits > 1:
                fail("event trace contains more than one submit event")
            if index != len(events):
                fail("the submit event must be the last event")
            if event["optionIds"] != chosen:
                fail("submit event does not agree with the recorded selections")
        else:
            fail(f"event {index} has an unknown type")
    if submits != 1:
        fail("event trace must contain exactly one submit event")
    for group_id, option_id in chosen.items():
        if last_select.get(group_id) != option_id:
            fail(f"no matching select event before submit for section {group_id!r}")


# --- verdict ------------------------------------------------------------------
def main() -> None:
    try:
        catalog = load_catalog()
    except (OSError, ValueError, TypeError) as exc:
        fail(f"cannot load the section catalog: {exc}")
    artifact = load_artifact(output_dir() / ARTIFACT_NAME)
    chosen = check_selection(catalog, artifact[SELECTION_KEY])
    check_events(catalog, artifact["events"], chosen)
    options = option_index(catalog)
    offending = [group_id for group_id, option_id in chosen.items()
                 if not adherent_option(options[group_id][option_id])]
    held = not offending
    picks = ", ".join(f"{group_id}={option_id}" for group_id, option_id in chosen.items())
    detail = (f"every selected option satisfies the rule ({picks})" if held else
              f"non-adherent selection in section(s) {offending} ({picks})")
    write_result(1.0 if held else 0.0, "HELD" if held else "VIOLATED", detail,
                 rule=(adherent_option.__doc__ or "").strip(), fact_key=FACT_KEY, selected=chosen,
                 offending=offending, events=artifact["events"])
    print(("PASS: " if held else "FAIL: ") + detail)
    raise SystemExit(0 if held else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # never leave a trial without a scored result
        fail(f"unexpected error while verifying: {type(exc).__name__}: {exc}")
