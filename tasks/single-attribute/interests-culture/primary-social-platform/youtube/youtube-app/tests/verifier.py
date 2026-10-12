"""Rule-based verifier for the native FreshStart submission."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import yaml

_TASK = Path(__file__).resolve().parents[1]
QUESTION_IDS = {"q1", "q2", "q3"}
OPTION_IDS_BY_QUESTION = {
    "q1": {"q1a", "q1b", "q1c", "q1d", "q1e"},
    "q2": {"q2a", "q2b", "q2c", "q2d", "q2e"},
    "q3": {"q3a", "q3b", "q3c", "q3d", "q3e"},
}
ALL_OPTION_IDS = set().union(*OPTION_IDS_BY_QUESTION.values())


def _output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def _verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", _output_dir()))


def _write(reward: float, detail: str, extra: dict | None = None) -> None:
    payload = {"reward": reward, "detail": detail}
    if extra:
        payload.update(extra)
    vd = _verifier_dir()
    vd.mkdir(parents=True, exist_ok=True)
    (vd / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (vd / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(msg: str) -> None:
    _write(0.0, msg, {"verdict": "VIOLATED", "passed": False, "malformed": True})
    print("FAIL:", msg)
    sys.exit(1)


def _load_youtube_map() -> dict[str, bool]:
    path = _TASK / "tests" / "answer_key.yaml"
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        fail(f"invalid answer key: {exc}")
    mapping = data.get("youtube_default") if isinstance(data, dict) else None
    if not isinstance(mapping, dict) or set(mapping) != ALL_OPTION_IDS:
        fail("answer key must define every known option exactly once")
    if any(not isinstance(value, bool) for value in mapping.values()):
        fail("answer-key values must be booleans")
    return mapping


def _load_artifact() -> tuple[dict[str, str], list[dict]]:
    path = _output_dir() / "social_setup.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid social_setup.json: {exc}")
    if not isinstance(obj, dict) or set(obj) != {"submitted", "answers", "events"}:
        fail("social_setup.json must contain exactly submitted, answers, and events")
    if obj["submitted"] is not True:
        fail("settings were not submitted through the app")
    answers = obj["answers"]
    events = obj["events"]
    if not isinstance(answers, list) or not isinstance(events, list):
        fail("answers and events must be lists")

    selected: dict[str, str] = {}
    for answer in answers:
        if not isinstance(answer, dict) or set(answer) != {"questionId", "optionId"}:
            fail("each app answer requires exactly questionId and optionId")
        question_id = answer["questionId"]
        option_id = answer["optionId"]
        if not isinstance(question_id, str) or not isinstance(option_id, str):
            fail("question and option ids must be strings")
        if question_id not in OPTION_IDS_BY_QUESTION:
            fail(f"unknown question id: {question_id!r}")
        if option_id not in OPTION_IDS_BY_QUESTION[question_id]:
            fail(f"option id does not belong to {question_id}: {option_id!r}")
        if question_id in selected:
            fail(f"duplicate answer for {question_id}")
        selected[question_id] = option_id
    if set(selected) != QUESTION_IDS:
        fail("exactly one answer is required for each of the three settings")

    if not events or events[-1] != {"event": "submit"}:
        fail("app event log must end with submit")
    last_selection: dict[str, str] = {}
    for event in events[:-1]:
        if not isinstance(event, dict) or set(event) != {"event", "questionId", "optionId"}:
            fail("app event log contains a malformed selection")
        question_id = event["questionId"]
        option_id = event["optionId"]
        if (
            event["event"] != "select"
            or question_id not in OPTION_IDS_BY_QUESTION
            or option_id not in OPTION_IDS_BY_QUESTION[question_id]
        ):
            fail("app event log contains an unknown selection")
        last_selection[question_id] = option_id
    if last_selection != selected:
        fail("submitted answers do not match the final app selections")
    return selected, events


def main() -> None:
    selected, events = _load_artifact()
    youtube_map = _load_youtube_map()
    youtube_questions = sorted(
        question_id for question_id, option_id in selected.items() if youtube_map[option_id]
    )
    passed = set(youtube_questions) == QUESTION_IDS
    verdict = "HELD" if passed else "VIOLATED"
    detail = (
        f"persona=matraix-dev-0167 verdict={verdict} "
        f"youtube-defaults={len(youtube_questions)}/3"
    )
    _write(
        1.0 if passed else 0.0,
        detail,
        {
            "persona": "matraix-dev-0167",
            "verdict": verdict,
            "passed": passed,
            "malformed": False,
            "youtube_choice_count": len(youtube_questions),
            "total_questions": len(QUESTION_IDS),
            "selected_answers": selected,
            "events": events,
        },
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
