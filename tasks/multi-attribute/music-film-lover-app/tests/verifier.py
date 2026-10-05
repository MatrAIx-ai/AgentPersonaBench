"""Independent two-check verifier for the music-and-film native-app task."""

from __future__ import annotations

import json
import os
from pathlib import Path

_DIMENSIONS = (
    ("topic_music", "Passionate", "music", "selected_music_events"),
    ("topic_film", "Passionate", "film", "selected_film_events"),
)


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write(payload: dict) -> None:
    target = _verifier_dir()
    target.mkdir(parents=True, exist_ok=True)
    (target / "reward.txt").write_text(f"{payload['reward']}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fail(message: str) -> None:
    _write(
        {
            "reward": 0.0,
            "score": "0/2",
            "points": 0,
            "max_points": 2,
            "passed_count": 0,
            "total_checks": 2,
            "criteria": [],
            "verdict": "ERROR",
            "detail": message,
        }
    )
    print("FAIL:", message)
    raise SystemExit(1)


def main() -> None:
    path = _output_dir() / "itinerary.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    events = source.get("selectedEvents")
    if not isinstance(events, list) or len(events) != 2 or not all(
        isinstance(event, dict) for event in events
    ):
        fail("itinerary.json must contain exactly two selectedEvents objects")
    ids = [event.get("id") for event in events]
    if any(not isinstance(event_id, str) or not event_id for event_id in ids) or len(set(ids)) != 2:
        fail("selectedEvents must carry two distinct non-empty ids")
    slots = [event.get("slot") for event in events]
    if sorted(slots) != ["friday", "saturday"]:
        fail("selectedEvents must contain one Friday and one Saturday event")
    if any(event.get("category") not in {"music", "film", "other"} for event in events):
        fail("every selected event must carry authoritative category metadata")

    criteria = []
    for dimension_id, value, category, metric in _DIMENSIONS:
        observed = sum(event["category"] == category for event in events)
        passed = observed >= 1
        criteria.append(
            {
                "dimension_id": dimension_id,
                "value": value,
                "metric": metric,
                "observed": observed,
                "threshold": ">= 1",
                "verdict": "HELD" if passed else "VIOLATED",
                "passed": passed,
            }
        )
    points = sum(criterion["passed"] for criterion in criteria)
    payload = {
        "reward": float(points),
        "score": f"{points}/2",
        "points": points,
        "max_points": 2,
        "passed_count": points,
        "total_checks": 2,
        "criteria": criteria,
        "persona": source.get("persona", "hf-synthetic-270713880"),
        "detail": "score={}/2 {}".format(
            points,
            ", ".join(
                f"{criterion['dimension_id']}={criterion['verdict']}"
                for criterion in criteria
            ),
        ),
    }
    _write(payload)
    print("PASS:", payload["detail"])
    raise SystemExit(0)


if __name__ == "__main__":
    main()
