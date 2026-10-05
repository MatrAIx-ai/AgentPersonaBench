"""Independent two-check verifier for the music-and-film web task."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

_TASK = Path(__file__).resolve().parents[1]
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


def _event_map() -> dict[str, dict[str, str]]:
    html = (_TASK / "input" / "site" / "index.html").read_text(encoding="utf-8")
    mapping = {
        match.group(1): {"slot": match.group(2), "category": match.group(3)}
        for match in re.finditer(
            r'class="event"\s+data-id="([^"]+)"\s+data-slot="([^"]+)"\s+data-category="([^"]+)"',
            html,
        )
    }
    if len(mapping) != 8:
        fail("could not parse all event ground truth from index.html")
    return mapping


def main() -> None:
    path = _output_dir() / "anchor" / "itinerary.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        selected = json.loads(path.read_text(encoding="utf-8")).get("selectedEventIds")
    except json.JSONDecodeError as exc:
        fail(f"{path} is not valid JSON: {exc}")
    if (
        not isinstance(selected, list)
        or len(selected) != 2
        or not all(isinstance(event_id, str) for event_id in selected)
        or len(set(selected)) != 2
    ):
        fail("itinerary.json must contain two distinct selectedEventIds")
    events = _event_map()
    unknown = [event_id for event_id in selected if event_id not in events]
    if unknown:
        fail(f"selected ids are not present in the page: {unknown}")
    slots = [events[event_id]["slot"] for event_id in selected]
    if sorted(slots) != ["friday", "saturday"]:
        fail("the itinerary must contain one Friday and one Saturday selection")

    criteria = []
    for dimension_id, value, category, metric in _DIMENSIONS:
        observed = sum(events[event_id]["category"] == category for event_id in selected)
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
    generation = {}
    generation_path = _output_dir() / "generation.json"
    if generation_path.is_file():
        generation = json.loads(generation_path.read_text(encoding="utf-8"))
    payload = {
        "reward": float(points),
        "score": f"{points}/2",
        "points": points,
        "max_points": 2,
        "passed_count": points,
        "total_checks": 2,
        "criteria": criteria,
        "persona": "hf-synthetic-270713880",
        "trajectory": generation.get("trajectory"),
        "generation": {"model": generation.get("model"), "calls": generation.get("calls")},
        "artifacts": {"trace": "trace.zip"},
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
