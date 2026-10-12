"""Rule-based verifier for the live volunteer portal."""
import json
import os
import sys
import tomllib
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
PERSONA = "synthetic-bca510aec772"
EXPECTED = {
    "skill_cooking": ("food", "Advanced"),
    "skill_baking": ("baking", "None"),
    "skill_photography": ("media", "Beginner"),
}


def output_dir():
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir():
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write(reward, detail, extra):
    target = verifier_dir()
    target.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )


def fail(message):
    write(0.0, message, {"passed": False})
    print("FAIL:", message)
    raise SystemExit(1)


def load_key():
    key = json.loads((TASK / "tests" / "answer_key.json").read_text(encoding="utf-8"))
    rooms = {"food", "baking", "media"}
    levels = {"None", "Beginner", "Intermediate", "Advanced", "Master"}
    if (not isinstance(key, dict) or len(key) != 12 or
            any(not isinstance(oid, str) or not isinstance(spec, dict) or
                set(spec) != {"room", "readiness"} or spec["room"] not in rooms or
                spec["readiness"] not in levels for oid, spec in key.items())):
        raise ValueError("invalid host-side answer key")
    return key


def validate_events(events, key, selected_by_room):
    if not isinstance(events, list) or not events:
        raise ValueError("events must be a non-empty list")
    viewed = []
    last_selected = {}
    submit_count = 0
    for index, event in enumerate(events):
        if not isinstance(event, dict) or not isinstance(event.get("type"), str):
            raise ValueError("each event must be an object with a string type")
        kind = event["type"]
        if kind == "view_role":
            if set(event) != {"type", "id"} or not isinstance(event.get("id"), str) or event["id"] not in key:
                raise ValueError("view_role has an unknown or wrong-typed id")
            viewed.append(event["id"])
        elif kind == "select_role":
            if (set(event) != {"type", "room", "id"} or
                    not isinstance(event.get("room"), str) or
                    not isinstance(event.get("id"), str) or event["id"] not in key or
                    key[event["id"]]["room"] != event["room"]):
                raise ValueError("select_role has invalid room/id data")
            if event["id"] not in viewed:
                raise ValueError("a role must be viewed before selection")
            last_selected[event["room"]] = event["id"]
        elif kind == "submit_assignments":
            if set(event) != {"type"} or index != len(events) - 1:
                raise ValueError("submit_assignments must be the final exact event")
            submit_count += 1
        else:
            raise ValueError(f"unknown event type {kind!r}")
    if submit_count != 1 or len(viewed) != 12 or set(viewed) != set(key):
        raise ValueError("events must view every role once and end with one submit")
    if last_selected != {room: item["id"] for room, item in selected_by_room.items()}:
        raise ValueError("final event selections do not match the submitted assignments")


def evaluate(record, checks):
    if not isinstance(record, dict) or set(record) != {"submitted", "viewed", "selected", "events"}:
        raise ValueError("artifact must contain exactly submitted, viewed, selected, and events")
    if record["submitted"] is not True:
        raise ValueError("assignments were not submitted")
    key = load_key()
    viewed = record["viewed"]
    if (not isinstance(viewed, list) or len(viewed) != 12 or
            any(not isinstance(item, str) for item in viewed) or
            len(set(viewed)) != 12 or set(viewed) != set(key)):
        raise ValueError("all 12 known role details must be reviewed exactly once")
    items = record["selected"]
    if not isinstance(items, list) or len(items) != 3:
        raise ValueError("exactly three assignments are required")
    by_room = {}
    for item in items:
        if (not isinstance(item, dict) or set(item) != {"room", "id"} or
                not isinstance(item["room"], str) or not isinstance(item["id"], str) or
                item["id"] not in key or key[item["id"]]["room"] != item["room"] or
                item["room"] in by_room):
            raise ValueError("each room requires one known role id with no extra labels")
        by_room[item["room"]] = item
    if set(by_room) != {"food", "baking", "media"}:
        raise ValueError("one assignment is required in each room")
    validate_events(record["events"], key, by_room)
    results = []
    for check in checks:
        dim = check["dimension_id"]
        room, expected = EXPECTED[dim]
        item = by_room[room]
        observed = key[item["id"]]["readiness"]
        held = observed == expected
        results.append({"evaluator": check.get("evaluator_name", dim), "dimension_id": dim,
                        "value": check["value"], "room": room, "selected_id": item["id"],
                        "observed_readiness": observed, "verdict": "HELD" if held else "VIOLATED",
                        "passed": held})
    return results


def main():
    path = output_dir() / "anchor" / "volunteer_assignments.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        with open(TASK / "task.toml", "rb") as stream:
            checks = tomllib.load(stream)["checks"]
        results = evaluate(record, checks)
    except Exception as exc:
        fail(f"invalid volunteer assignment artifact: {exc}")
    points = sum(item["passed"] for item in results)
    total = len(results)
    detail = f"persona={PERSONA} score {points}/{total}: " + ", ".join(
        f"{item['dimension_id']}={item['verdict']}" for item in results
    )
    write(float(points), detail, {"persona": PERSONA, "criteria": results, "checks": results,
          "score": f"{points}/{total}", "points": points, "max_points": total,
          "passed_count": points, "total_checks": total, "completed": True,
          "selected": record["selected"]})
    print(detail)
    raise SystemExit(0)


if __name__ == "__main__":
    main()
