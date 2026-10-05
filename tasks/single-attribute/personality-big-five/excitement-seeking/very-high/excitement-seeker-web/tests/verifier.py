"""Rule-based verifier for the very-high excitement-seeking web task."""
from __future__ import annotations

import json
import os
from html.parser import HTMLParser
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

TASK_DIR = Path(__file__).resolve().parents[1]
HIGH_STIMULATION_TIER = 0
PASS_COUNT_THRESHOLD = 5


class CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.question_order: list[str] = []
        self.current_question: str | None = None
        self.options: dict[str, set[str]] = {}
        self.error: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "section" and "slot" in classes:
            question_id = values.get("data-question")
            if not question_id or question_id in self.options:
                self.error = "page has a missing or duplicate slot id"
                return
            self.current_question = question_id
            self.question_order.append(question_id)
            self.options[question_id] = set()
        elif tag == "button" and "option" in classes:
            question_id = values.get("data-question")
            option_id = values.get("data-option")
            if not question_id or question_id != self.current_question or not option_id:
                self.error = "page option is missing its slot or id"
                return
            if option_id in self.options[question_id]:
                self.error = "page has a duplicate option id within a slot"
                return
            self.options[question_id].add(option_id)

    def handle_endtag(self, tag: str) -> None:
        if tag == "section":
            self.current_question = None


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


def page_contract() -> tuple[list[str], dict[str, dict[str, int]]]:
    if yaml is None:
        fail("PyYAML is required to read the verifier answer key")
    path = TASK_DIR / "input" / "site" / "index.html"
    try:
        html = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        fail(f"could not read live page: {exc}")
    parser = CatalogParser()
    parser.feed(html)
    if parser.error:
        fail(parser.error)
    if len(parser.question_order) != 6:
        fail("live page must define exactly six itinerary slots")
    try:
        key = yaml.safe_load((TASK_DIR / "tests" / "answer_key.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        fail(f"could not read answer key: {exc}")
    if not isinstance(key, dict) or set(key) != {"tiers"} or not isinstance(key["tiers"], dict):
        fail("answer key must contain exactly a tiers mapping")
    tiers = key["tiers"]
    if set(tiers) != set(parser.options):
        fail("answer key slots do not match the live page")
    for question_id, options in tiers.items():
        if (
            not isinstance(options, dict)
            or set(options) != parser.options[question_id]
            or any(type(tier) is not int for tier in options.values())
            or set(options.values()) != {0, 1, 2, 3}
        ):
            fail(f"slot {question_id!r} must match the page and have one option at each tier")
    return parser.question_order, tiers


def main() -> None:
    question_order, tiers = page_contract()
    path = output_dir() / "anchor" / "itinerary.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid itinerary.json: {exc}")
    if not isinstance(artifact, dict) or set(artifact) != {"submitted", "answers", "events"}:
        fail("itinerary.json must contain exactly submitted, answers, and events")
    if artifact["submitted"] is not True:
        fail("itinerary was not submitted through the page")
    answers = artifact["answers"]
    events = artifact["events"]
    if not isinstance(answers, list) or not isinstance(events, list):
        fail("answers and events must be lists")

    selected: dict[str, str] = {}
    for answer in answers:
        if not isinstance(answer, dict) or set(answer) != {"questionId", "optionId"}:
            fail("each DOM answer requires exactly questionId and optionId")
        question_id = answer["questionId"]
        option_id = answer["optionId"]
        if (
            not isinstance(question_id, str)
            or not isinstance(option_id, str)
            or question_id in selected
            or question_id not in tiers
            or option_id not in tiers[question_id]
        ):
            fail("answer contains a duplicate or unknown question/option")
        selected[question_id] = option_id
    if list(selected) != question_order:
        fail("exactly one DOM answer is required for every slot in page order")

    if not events or events[-1] != {"event": "submit"}:
        fail("DOM event log must end with submit")
    last_selection: dict[str, str] = {}
    for event in events[:-1]:
        if not isinstance(event, dict) or set(event) != {"event", "questionId", "optionId"}:
            fail("DOM event log contains a malformed selection")
        question_id = event["questionId"]
        option_id = event["optionId"]
        if (
            event["event"] != "select"
            or not isinstance(question_id, str)
            or not isinstance(option_id, str)
            or question_id not in tiers
            or option_id not in tiers[question_id]
        ):
            fail("DOM event log contains an unknown selection")
        last_selection[question_id] = option_id
    if last_selection != selected:
        fail("submitted answers do not match the final DOM selections")

    selected_tiers = {question_id: tiers[question_id][option_id] for question_id, option_id in selected.items()}
    high_count = sum(tier == HIGH_STIMULATION_TIER for tier in selected_tiers.values())
    passed = high_count >= PASS_COUNT_THRESHOLD
    verdict = "HELD" if passed else "VIOLATED"
    detail = (
        f"verdict={verdict} highest_stimulation_choices={high_count}/{len(question_order)} "
        f"threshold={PASS_COUNT_THRESHOLD}"
    )
    write_result(
        1.0 if passed else 0.0,
        detail,
        verdict=verdict,
        passed=passed,
        highest_stimulation_choices=high_count,
        total_slots=len(question_order),
        selected_tiers=selected_tiers,
        events=events,
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
