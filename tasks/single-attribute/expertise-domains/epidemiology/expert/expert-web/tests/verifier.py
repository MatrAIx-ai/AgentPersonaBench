"""Verifier for the submitted DOM state of the Study Design Console."""
from __future__ import annotations

import json
import os
from pathlib import Path

import yaml

TASK_DIR = Path(__file__).resolve().parents[1]
STUDY_ORDER = ("st-a4", "st-h7", "st-m3", "st-p9")
FIELD_ORDER = ("adjustment", "estimand", "claim")
MAX_EVENTS = 100
OPTIONS = {
    "st-a4": {
        "adjustment": {"a4-k2", "a4-p8", "a4-v5"},
        "estimand": {"a4-s1", "a4-e7", "a4-n9"},
        "claim": {"a4-r3", "a4-z8", "a4-c6"},
    },
    "st-h7": {
        "adjustment": {"h7-f4", "h7-b9", "h7-l2"},
        "estimand": {"h7-q6", "h7-t1", "h7-w8"},
        "claim": {"h7-y3", "h7-d5", "h7-a7"},
    },
    "st-m3": {
        "adjustment": {"m3-j8", "m3-c1", "m3-r6"},
        "estimand": {"m3-p2", "m3-u9", "m3-e4"},
        "claim": {"m3-n5", "m3-g7", "m3-x3"},
    },
    "st-p9": {
        "adjustment": {"p9-v2", "p9-a6", "p9-h4"},
        "estimand": {"p9-k8", "p9-f1", "p9-s7"},
        "claim": {"p9-m3", "p9-q5", "p9-d9"},
    },
}


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(verdict: str, detail: str, **extra: object) -> None:
    reward = 1.0 if verdict == "HELD" else 0.0
    out = verifier_dir()
    out.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, "verdict": verdict, "passed": verdict == "HELD", **extra}
    (out / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (out / "structured_output.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def abort(message: str) -> None:
    write_result("ERROR", message, error_stage="artifact_validation")
    print("ERROR:", message)
    raise SystemExit(2)


def read_key() -> tuple[dict, dict]:
    try:
        obj = yaml.safe_load((TASK_DIR / "tests" / "answer_key.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        abort(f"invalid host answer key: {exc}")
    if not isinstance(obj, dict) or set(obj) != {"tiers", "rationales"}:
        abort("host answer key must contain exactly tiers and rationales")
    tiers, rationales = obj["tiers"], obj["rationales"]
    if not isinstance(tiers, dict) or not isinstance(rationales, dict):
        abort("host answer key sections must be mappings")
    if set(tiers) != set(STUDY_ORDER) or set(rationales) != set(STUDY_ORDER):
        abort("host answer key study set mismatch")
    for study_id in STUDY_ORDER:
        if not isinstance(tiers[study_id], dict) or set(tiers[study_id]) != set(FIELD_ORDER):
            abort(f"host answer key field set mismatch for {study_id}")
        for field_id in FIELD_ORDER:
            mapping = tiers[study_id][field_id]
            if not isinstance(mapping, dict) or set(mapping) != OPTIONS[study_id][field_id]:
                abort(f"host answer key option set mismatch for {study_id}/{field_id}")
            if any(type(tier) is not int or tier not in {0, 1, 2, 3} for tier in mapping.values()):
                abort(f"invalid host tier for {study_id}/{field_id}")
        if not isinstance(rationales[study_id], str) or not rationales[study_id].strip():
            abort(f"invalid host rationale for {study_id}")
    return tiers, rationales


def read_artifact() -> tuple[dict[str, dict[str, str]], list[dict], dict]:
    path = output_dir() / "anchor" / "causal_console_review.json"
    if not path.is_file():
        abort(f"missing {path}")
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        abort(f"invalid causal_console_review.json: {exc}")
    if not isinstance(obj, dict) or set(obj) != {"submitted", "reviews", "events", "confirmation"}:
        abort("console artifact must contain exactly submitted, reviews, events, and confirmation")
    if obj["submitted"] is not True:
        abort("console audit was not submitted")
    reviews, events, confirmation = obj["reviews"], obj["events"], obj["confirmation"]
    if not isinstance(reviews, list) or len(reviews) != len(STUDY_ORDER):
        abort(f"exactly {len(STUDY_ORDER)} study reviews are required")
    if not isinstance(events, list) or not events:
        abort("events must be a non-empty list")
    if len(events) > MAX_EVENTS:
        abort(f"event log exceeds limit {MAX_EVENTS}")
    if not isinstance(confirmation, dict) or set(confirmation) != {"status", "reviewCount", "inspectionCount", "selectionCount"}:
        abort("confirmation has an invalid schema")
    if confirmation["status"] != "submitted" or type(confirmation["reviewCount"]) is not int or type(confirmation["inspectionCount"]) is not int or type(confirmation["selectionCount"]) is not int:
        abort("confirmation values have invalid types or status")

    selected: dict[str, dict[str, str]] = {}
    for index, review in enumerate(reviews):
        if not isinstance(review, dict) or set(review) != {"studyId", "adjustmentId", "estimandId", "claimId"}:
            abort(f"review {index} has an invalid schema")
        study_id = review["studyId"]
        if not isinstance(study_id, str) or study_id not in OPTIONS:
            abort(f"review {index} has an unknown study id")
        if study_id in selected:
            abort(f"duplicate review for {study_id}")
        selected[study_id] = {}
        for field_id in FIELD_ORDER:
            option_id = review[f"{field_id}Id"]
            if not isinstance(option_id, str) or option_id not in OPTIONS[study_id][field_id]:
                abort(f"unknown or cross-study option for {study_id}/{field_id}: {option_id!r}")
            selected[study_id][field_id] = option_id
    if set(selected) != set(STUDY_ORDER):
        abort("one review is required for every study")

    if events[-1] != {"event": "submit"}:
        abort("DOM event log must end with one submit event")
    last: dict[str, dict[str, str]] = {}
    inspected: set[str] = set()
    selection_count = 0
    for index, event in enumerate(events[:-1]):
        if isinstance(event, dict) and set(event) == {"event", "studyId"}:
            study_id = event["studyId"]
            if event["event"] != "inspect" or study_id not in OPTIONS or study_id in inspected:
                abort(f"inspection event {index} is unknown or duplicated")
            inspected.add(study_id)
            continue
        if not isinstance(event, dict) or set(event) != {"event", "studyId", "fieldId", "optionId"}:
            abort(f"selection event {index} has an invalid schema")
        study_id, field_id, option_id = event["studyId"], event["fieldId"], event["optionId"]
        if event["event"] != "select" or study_id not in OPTIONS or field_id not in FIELD_ORDER:
            abort(f"selection event {index} has an unknown study or field")
        if study_id not in inspected:
            abort(f"selection event {index} occurred before its evidence panel was inspected")
        if not isinstance(option_id, str) or option_id not in OPTIONS[study_id][field_id]:
            abort(f"selection event {index} has an unknown option")
        last.setdefault(study_id, {})[field_id] = option_id
        selection_count += 1
    if last != selected:
        abort("submitted reviews contradict the final live DOM selections")
    if confirmation["reviewCount"] != len(reviews):
        abort("confirmation review count does not match submitted reviews")
    if inspected != set(STUDY_ORDER) or confirmation["inspectionCount"] != len(inspected):
        abort("confirmation does not prove every design-evidence panel was inspected")
    if confirmation["selectionCount"] != selection_count:
        abort("confirmation selection count does not match the event log")
    return selected, events, confirmation


def main() -> None:
    selected, events, confirmation = read_artifact()
    tiers, rationales = read_key()
    field_results = []
    material_errors = []
    for study_id in STUDY_ORDER:
        for field_id in FIELD_ORDER:
            option_id = selected[study_id][field_id]
            tier = tiers[study_id][field_id][option_id]
            result = {"studyId": study_id, "fieldId": field_id, "optionId": option_id, "tier": tier}
            field_results.append(result)
            if tier >= 2:
                material_errors.append({**result, "rationale": rationales[study_id]})
    verdict = "HELD" if not material_errors else "VIOLATED"
    detail = f"verdict={verdict} completed_fields={len(field_results)}/12 material_errors={len(material_errors)}"
    write_result(verdict, detail, selected_reviews=selected, field_results=field_results, material_errors=material_errors, confirmation=confirmation, events=events)
    print(("PASS: " if verdict == "HELD" else "FAIL: ") + detail)
    raise SystemExit(0 if verdict == "HELD" else 1)


if __name__ == "__main__":
    main()
