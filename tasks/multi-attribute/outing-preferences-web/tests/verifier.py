"""Strict rule-based verifier for Weekend Board."""
from __future__ import annotations

import json
import os
import sys
import tomllib
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
PERSONA = "synthetic-8de90dcf8ceb"


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, payload: dict) -> None:
    target = verifier_dir(); target.mkdir(parents=True, exist_ok=True)
    data = {"reward": reward, "detail": detail, **payload}
    (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(message: str) -> None:
    write_result(0.0, message, {"verdict": "VIOLATED", "passed": False})
    print(f"FAIL: {message}"); raise SystemExit(1)


def event_indices(events: list, name: str, activity_id: str) -> list[int]:
    return [index for index, event in enumerate(events)
            if isinstance(event, dict) and event == {"event": name, "activityId": activity_id}]


def main() -> None:
    source = output_dir() / "anchor" / "booking.json"
    if not source.is_file():
        fail(f"missing {source}")
    try:
        artifact = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid booking.json: {exc}")
    if not isinstance(artifact, dict) or set(artifact) != {"state", "selectedActivity", "detailsOpened", "events"}:
        fail("booking.json has an invalid schema")
    if artifact["state"] != "submitted" or not isinstance(artifact["selectedActivity"], dict):
        fail("a submitted activity is required")
    if not isinstance(artifact["detailsOpened"], list) or not isinstance(artifact["events"], list):
        fail("detailsOpened and events must be lists")
    key = json.loads((TASK / "tests" / "answer_key.json").read_text(encoding="utf-8"))
    selected = artifact["selectedActivity"]
    if set(selected) != {"id", "name"}:
        fail("selectedActivity must contain exactly id and name")
    if not isinstance(selected["id"], str) or not isinstance(selected["name"], str):
        fail("selectedActivity id and name must be strings")
    if selected["id"] not in key:
        fail("selectedActivity must be a known app-derived id and name")
    activity_id = selected["id"]
    if selected["name"] != key[activity_id]["name"]:
        fail("selected activity name does not match its id")
    opened = artifact["detailsOpened"]
    if any(not isinstance(item, str) for item in opened):
        fail("detailsOpened entries must be string activity ids")
    if len(opened) != len(set(opened)) or any(item not in key for item in opened) or activity_id not in opened:
        fail("the selected activity's full details must have been opened")
    events = artifact["events"]
    allowed_events = {"view_details", "select_activity", "confirm_booking"}
    if any(not isinstance(event, dict) or set(event) != {"event", "activityId"}
           or not isinstance(event["event"], str) or event["event"] not in allowed_events
           or not isinstance(event["activityId"], str) or event["activityId"] not in key
           for event in events):
        fail("events must contain known string event names and activity ids")
    views = event_indices(events, "view_details", activity_id)
    selects = event_indices(events, "select_activity", activity_id)
    confirms = event_indices(events, "confirm_booking", activity_id)
    if not views or not selects or not confirms or not (views[0] < selects[-1] < confirms[-1]):
        fail("expected ordered view, selection, and confirmation events")

    observations = {
        "topic_pets": (key[activity_id]["pet_related"] is False, key[activity_id]["pet_related"]),
        "topic_hiking": (key[activity_id]["hiking"] is True, key[activity_id]["hiking"]),
    }
    with (TASK / "task.toml").open("rb") as handle:
        checks = tomllib.load(handle)["checks"]
    criteria = []
    for check in checks:
        held, observed = observations[check["dimension_id"]]
        criteria.append({"evaluator": check["dimension_id"], "dimension_id": check["dimension_id"],
                         "value": check["value"], "observed": observed,
                         "verdict": "HELD" if held else "VIOLATED", "passed": held})
    points, total = sum(item["passed"] for item in criteria), len(criteria)
    detail = f"score {points}/{total}: selected={activity_id}; " + ", ".join(
        f"{item['dimension_id']}={item['verdict']}" for item in criteria)
    write_result(float(points), detail, {"persona": PERSONA, "criteria": criteria, "checks": criteria,
        "score": f"{points}/{total}", "points": points, "max_points": total,
        "passed_count": points, "total_checks": total, "selected_activity": selected,
        "details_opened": opened, "events": artifact["events"]})
    print(detail); raise SystemExit(0 if points == total else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        fail(f"verifier rejected malformed input: {type(exc).__name__}")
