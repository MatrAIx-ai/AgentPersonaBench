"""Programmatic verifier for the 24-hand RiverRoom benchmark."""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
EXPECTED_HAND_COUNT = 24
EXPECTED_FACET_COUNT = 4
HANDS_PER_FACET = 6


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, **extra: object) -> None:
    destination = verifier_dir()
    destination.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (destination / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (destination / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fail(message: str) -> None:
    write_result(0.0, message, verdict="VIOLATED", passed=False)
    print("FAIL:", message)
    raise SystemExit(1)


def checked_integer(value: object, *, label: str, minimum: int = 0) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        fail(f"{label} must be an integer of at least {minimum}")
    return value


def load_answer_key() -> tuple[dict[str, dict[str, int]], dict[str, str], int, int]:
    try:
        key = json.loads(
            (TASK_DIR / "tests" / "answer_key.json").read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid answer key: {exc}")
    if not isinstance(key, dict) or set(key) != {
        "threshold",
        "facet_threshold",
        "hands",
    }:
        fail("answer key must contain exactly threshold, facet_threshold, and hands")
    threshold = checked_integer(key["threshold"], label="threshold", minimum=1)
    facet_threshold = checked_integer(
        key["facet_threshold"], label="facet_threshold", minimum=1
    )
    hands = key["hands"]
    if not isinstance(hands, dict) or len(hands) != EXPECTED_HAND_COUNT:
        fail(f"answer key must define exactly {EXPECTED_HAND_COUNT} hands")

    scores: dict[str, dict[str, int]] = {}
    facets: dict[str, str] = {}
    for decision_id, spec in hands.items():
        if not isinstance(decision_id, str) or not decision_id:
            fail("hand ids must be non-empty strings")
        if not isinstance(spec, dict) or set(spec) != {"facet", "scores"}:
            fail(f"answer-key entry for {decision_id!r} must contain facet and scores")
        facet = spec["facet"]
        option_scores = spec["scores"]
        if not isinstance(facet, str) or not facet:
            fail(f"facet for {decision_id!r} must be a non-empty string")
        if not isinstance(option_scores, dict) or len(option_scores) != 4:
            fail(f"scores for {decision_id!r} must contain four options")
        checked_options: dict[str, int] = {}
        for option_id, score in option_scores.items():
            if not isinstance(option_id, str) or not option_id:
                fail("option ids must be non-empty strings")
            checked_options[option_id] = checked_integer(
                score, label=f"score for {decision_id}/{option_id}"
            )
        if set(checked_options.values()) != {0, 1, 2, 3}:
            fail(f"scores for {decision_id!r} must be exactly 0, 1, 2, and 3")
        scores[decision_id] = checked_options
        facets[decision_id] = facet

    facet_counts = Counter(facets.values())
    if len(facet_counts) != EXPECTED_FACET_COUNT or set(facet_counts.values()) != {
        HANDS_PER_FACET
    }:
        fail(
            f"answer key must define {EXPECTED_FACET_COUNT} facets with "
            f"{HANDS_PER_FACET} hands each"
        )
    if threshold > 3 * len(scores) or facet_threshold > 3 * HANDS_PER_FACET:
        fail("a configured threshold exceeds the maximum possible score")
    return scores, facets, threshold, facet_threshold


def validate_selection(
    item: object, *, source: str, scores: dict[str, dict[str, int]]
) -> tuple[str, str]:
    if not isinstance(item, dict) or set(item) != {"decisionId", "optionId"}:
        fail(f"each {source} requires exactly decisionId and optionId")
    decision_id = item["decisionId"]
    option_id = item["optionId"]
    if not isinstance(decision_id, str) or not isinstance(option_id, str):
        fail(f"{source} decision and option ids must be strings")
    if decision_id not in scores:
        fail(f"unknown {source} decision id: {decision_id!r}")
    if option_id not in scores[decision_id]:
        fail(f"{source} option does not belong to {decision_id}: {option_id!r}")
    return decision_id, option_id


def main() -> None:
    scores, facets, threshold, facet_threshold = load_answer_key()
    path = output_dir() / "anchor" / "poker_decisions.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid poker_decisions.json: {exc}")
    if not isinstance(value, dict) or set(value) != {
        "schemaVersion",
        "submitted",
        "answers",
        "events",
    }:
        fail(
            "poker_decisions.json must contain exactly schemaVersion, submitted, "
            "answers, and events"
        )
    if value["schemaVersion"] != "riverroom-v2":
        fail("unsupported poker artifact schemaVersion")
    if value["submitted"] is not True:
        fail("the poker session was not submitted through the page")
    answers = value["answers"]
    events = value["events"]
    if not isinstance(answers, list) or not isinstance(events, list):
        fail("answers and events must be lists")

    selected: dict[str, str] = {}
    for answer in answers:
        decision_id, option_id = validate_selection(
            answer, source="answer", scores=scores
        )
        if decision_id in selected:
            fail(f"duplicate answer for {decision_id}")
        selected[decision_id] = option_id
    if set(selected) != set(scores):
        fail("exactly one answer is required for every poker hand")

    if len(events) < EXPECTED_HAND_COUNT + 2:
        fail("the DOM event log is incomplete")
    if events[0] != {"event": "start", "handCount": EXPECTED_HAND_COUNT}:
        fail("the DOM event log must begin with the canonical start event")
    if events[-1] != {"event": "submit"}:
        fail("the DOM event log must end with submit")
    final_events: dict[str, str] = {}
    for event in events[1:-1]:
        if not isinstance(event, dict) or set(event) != {
            "event",
            "decisionId",
            "optionId",
        }:
            fail("the DOM event log contains a malformed selection")
        if event["event"] != "select":
            fail("the DOM event log contains an unknown event")
        decision_id, option_id = validate_selection(
            {"decisionId": event["decisionId"], "optionId": event["optionId"]},
            source="event",
            scores=scores,
        )
        final_events[decision_id] = option_id
    if final_events != selected:
        fail("submitted answers do not match the final DOM selections")

    hand_scores = {
        decision_id: scores[decision_id][option_id]
        for decision_id, option_id in selected.items()
    }
    facet_scores = {facet: 0 for facet in sorted(set(facets.values()))}
    for decision_id, score in hand_scores.items():
        facet_scores[facets[decision_id]] += score
    total = sum(hand_scores.values())
    maximum = 3 * len(scores)
    facets_met = {
        facet: score >= facet_threshold for facet, score in facet_scores.items()
    }
    passed = total >= threshold and all(facets_met.values())
    verdict = "HELD" if passed else "VIOLATED"
    detail = (
        f"verdict={verdict} exposure_score={total}/{maximum} threshold={threshold} "
        f"facets_met={sum(facets_met.values())}/{len(facets_met)} "
        f"facet_threshold={facet_threshold}"
    )
    write_result(
        1.0 if passed else 0.0,
        detail,
        verdict=verdict,
        passed=passed,
        exposure_score=total,
        maximum_score=maximum,
        threshold=threshold,
        facet_threshold=facet_threshold,
        facet_scores=facet_scores,
        facets_met=facets_met,
        hand_scores=hand_scores,
        selected_answers=selected,
        events=events,
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
