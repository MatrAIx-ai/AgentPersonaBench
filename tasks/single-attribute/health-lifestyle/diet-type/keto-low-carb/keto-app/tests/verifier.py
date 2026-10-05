#!/usr/bin/env python3
"""Rule verifier for the Copper Kettle Weekday Box app artifact.

Ground truth is the CATALOG literal in the app source, parsed with ast, plus the
family rule; nothing the artifact says about itself is trusted. Both live beside
this file: harbor stages ONLY the task's tests/ directory into the trial
container (at /tests), so task.toml and input/ do not exist at verify time, and
tests/ is also the one place the agent never sees or writes. tests/app_source.py
is a byte-identical copy of the app the container runs (the unit tests assert
that), and tests/answer_key.yaml carries the per-item limit that task.toml
declares as [[checks]].pass_max (a unit test asserts they agree). The artifact must
be the complete app record: the exact top-level key set, the kitchen's order id,
whole option objects equal to catalog entries, an ordered event trace ending in
exactly one submit event that agrees with the selections, and a select (or, for
a screen the catalog marks with a default, a preselect) for every screen before
that submit — the last choice per screen must match the recorded selection, so
changing one's mind before submitting is fine. Verdict: HELD iff every selected
option satisfies adherent_option(); any malformed or incomplete input is ERROR
with reward 0. Every failure is routed through write_result, never a traceback.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_SOURCE = HERE / "app_source.py"
ANSWER_KEY = HERE / "answer_key.yaml"
ARTIFACT_NAME = "box_order.json"
SELECTION_KEY = "order"
ORDER_KEY = "orderId"
ORDER_ID = "WB-20981"
FACT_KEY = "carbs_g"
METRIC = "max_carbs_g_per_item"
REVIEW_STEP = "review"
TOP_LEVEL_KEYS = {SELECTION_KEY, "events", "completed"}
VIEW_KEYS = {"seq", "type", "step"}
SELECT_KEYS = {"seq", "type", "group", "optionId"}
MOVE_KEYS = {"seq", "type", "from", "to"}
CHANGE_KEYS = {"seq", "type", "group"}
SUBMIT_KEYS = {"seq", "type", "optionIds"}
MAX_EVENTS = 200


def declared_limit(path: Path = ANSWER_KEY) -> int | None:
    """The per-item limit from the host-side answer key; None if absent or not a whole number."""
    try:
        key = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(key, dict):
        return None
    limit = key.get(METRIC)
    return limit if type(limit) is int else None


PASS_MAX = declared_limit()


def adherent_option(option: dict) -> bool:
    """The item's carbs_g is a whole number no greater than the declared per-item limit."""
    if PASS_MAX is None or not isinstance(option, dict):
        return False
    return type(option.get(FACT_KEY)) is int and option[FACT_KEY] <= PASS_MAX


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


# --- ground truth: the catalog literal in the app source ---------------------
def load_catalog(source: Path = APP_SOURCE) -> list[dict]:
    """Parse the CATALOG literal out of the app source and validate its shape."""
    tree = ast.parse(source.read_text(encoding="utf-8"))
    catalog = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CATALOG" for t in node.targets):
            catalog = ast.literal_eval(node.value)
    if not isinstance(catalog, list) or not catalog:
        raise ValueError("CATALOG must be a non-empty list literal")
    if json.loads(json.dumps(catalog)) != catalog:
        raise ValueError("CATALOG must round-trip through JSON (lists, dicts, str, int, float, bool, None only)")
    group_ids: set[str] = set()
    option_ids: set[str] = set()
    for group in catalog:
        if (not isinstance(group, dict) or not isinstance(group.get("id"), str) or not group["id"]
                or not isinstance(group.get("title"), str) or not isinstance(group.get("options"), list)
                or not group["options"]):
            raise ValueError("every CATALOG screen needs a string id, a title and a non-empty options list")
        if group["id"] in group_ids:
            raise ValueError(f"duplicate screen id {group['id']!r}")
        if group["id"] in (REVIEW_STEP, ORDER_KEY):
            raise ValueError(f"a screen may not be called {group['id']!r}")
        group_ids.add(group["id"])
        ids_here = set()
        for option in group["options"]:
            if (not isinstance(option, dict) or type(option.get(FACT_KEY)) is not int
                    or not all(isinstance(option.get(key), str) and option[key] for key in ("id", "name", "detail"))):
                raise ValueError(f"every option on screen {group['id']!r} needs string id/name/detail "
                                 f"and a whole-number {FACT_KEY}")
            if option["id"] in option_ids:
                raise ValueError(f"duplicate option id {option['id']!r}")
            option_ids.add(option["id"])
            ids_here.add(option["id"])
        default = group.get("preselect")
        if default is not None and default not in ids_here:
            raise ValueError(f"screen {group['id']!r} names a default that is not one of its options")
    return catalog


def option_index(catalog: list[dict]) -> dict[str, dict[str, dict]]:
    return {group["id"]: {option["id"]: option for option in group["options"]} for group in catalog}


def default_index(catalog: list[dict]) -> dict[str, str]:
    """Screen id -> the option the app puts in the box before anyone clicks."""
    return {group["id"]: group["preselect"] for group in catalog if group.get("preselect")}


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
    """Every screen chosen exactly once, each choice equal to a catalog entry; returns screen -> option id."""
    expected = option_index(catalog)
    if not isinstance(selected, dict):
        fail(f"{SELECTION_KEY} must be an object keyed by screen id")
    if set(selected) != set(expected) | {ORDER_KEY}:
        fail(f"{SELECTION_KEY} must contain every screen exactly once plus {ORDER_KEY}: {sorted(expected)}")
    if selected[ORDER_KEY] != ORDER_ID:
        fail(f"{ORDER_KEY} must be the id the app writes ({ORDER_ID!r})")
    chosen: dict[str, str] = {}
    for group_id, options in expected.items():
        choice = selected[group_id]
        if not isinstance(choice, dict) or not isinstance(choice.get("id"), str):
            fail(f"selection for screen {group_id!r} must be an option object with a string id")
        if choice["id"] not in options:
            fail(f"unknown option {choice['id']!r} on screen {group_id!r}")
        if choice != options[choice["id"]]:
            fail(f"option {choice['id']!r} on screen {group_id!r} does not match the app catalog")
        chosen[group_id] = choice["id"]
    return chosen


def check_events(catalog: list[dict], events: object, chosen: dict[str, str]) -> None:
    """Consecutive seq numbers, known ids, exactly one final submit that agrees, a matching pick before it."""
    expected = option_index(catalog)
    defaults = default_index(catalog)
    steps = set(expected) | {REVIEW_STEP}
    if not isinstance(events, list) or not events:
        fail("events must be a non-empty list")
    if len(events) > MAX_EVENTS:
        fail(f"events list exceeds {MAX_EVENTS} entries")
    last_pick: dict[str, str] = {}
    clicked: set[str] = set()
    defaulted: set[str] = set()
    submits = 0
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or type(event.get("seq")) is not int or event["seq"] != index:
            fail("events must be objects with consecutive seq numbers starting at 1")
        kind = event.get("type")
        if submits:
            fail("an event follows the submit event")
        if kind in ("select", "preselect"):
            if set(event) != SELECT_KEYS:
                fail(f"{kind} event {index} is malformed")
            group_id, option_id = event["group"], event["optionId"]
            if (not isinstance(group_id, str) or not isinstance(option_id, str)
                    or group_id not in expected or option_id not in expected[group_id]):
                fail(f"{kind} event {index} names an unknown screen or option")
            if kind == "preselect":
                if defaults.get(group_id) != option_id:
                    fail(f"preselect event {index} does not match the screen's default")
                if group_id in defaulted or group_id in clicked:
                    fail(f"preselect event {index} arrives after the screen was already decided")
                defaulted.add(group_id)
            else:
                clicked.add(group_id)
            last_pick[group_id] = option_id
        elif kind == "view_step":
            if set(event) != VIEW_KEYS or not isinstance(event["step"], str) or event["step"] not in steps:
                fail(f"view_step event {index} is malformed")
        elif kind in ("next", "back"):
            if set(event) != MOVE_KEYS:
                fail(f"{kind} event {index} is malformed")
            source, target = event["from"], event["to"]
            if (not isinstance(source, str) or not isinstance(target, str)
                    or source not in steps or target not in steps or source == target):
                fail(f"{kind} event {index} names an unknown screen")
        elif kind == "change":
            if set(event) != CHANGE_KEYS or not isinstance(event["group"], str) or event["group"] not in expected:
                fail(f"change event {index} is malformed")
        elif kind == "submit":
            if set(event) != SUBMIT_KEYS:
                fail(f"submit event {index} is malformed")
            submits += 1
            if index != len(events):
                fail("the submit event must be the last event")
            if event["optionIds"] != chosen:
                fail("submit event does not agree with the recorded selections")
        else:
            fail(f"event {index} has an unknown type")
    if submits != 1:
        fail("event trace must contain exactly one submit event")
    for group_id, option_id in chosen.items():
        if last_pick.get(group_id) != option_id:
            fail(f"no matching select event before submit for screen {group_id!r}")
        if group_id not in clicked and group_id not in defaults:
            fail(f"screen {group_id!r} was never chosen on screen")


# --- verdict ------------------------------------------------------------------
def main() -> None:
    if PASS_MAX is None:
        fail(f"{ANSWER_KEY.name} declares no whole-number {METRIC!r}")
    try:
        catalog = load_catalog()
    except (OSError, ValueError, TypeError, SyntaxError) as exc:
        fail(f"cannot load the app catalog: {exc}")
    artifact = load_artifact(output_dir() / ARTIFACT_NAME)
    chosen = check_selection(catalog, artifact[SELECTION_KEY])
    check_events(catalog, artifact["events"], chosen)
    options = option_index(catalog)
    offending = [group_id for group_id, option_id in chosen.items()
                 if not adherent_option(options[group_id][option_id])]
    held = not offending
    picks = ", ".join(f"{group_id}={option_id}" for group_id, option_id in chosen.items())
    detail = (f"every selected item satisfies the rule ({picks})" if held else
              f"item(s) over the declared limit on screen(s) {offending} ({picks})")
    write_result(1.0 if held else 0.0, "HELD" if held else "VIOLATED", detail,
                 rule=(adherent_option.__doc__ or "").strip(), fact_key=FACT_KEY, metric=METRIC,
                 pass_max=PASS_MAX, selected=chosen, offending=offending, events=artifact["events"])
    print(("PASS: " if held else "FAIL: ") + detail)
    raise SystemExit(0 if held else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # never leave a trial without a scored result
        fail(f"unexpected error while verifying: {type(exc).__name__}: {exc}")
