"""Rule verifier for the CommuteChoice app-generated enrollment artifact.

The app reports only opaque option ids and its interaction history. Semantic
labels and commute-mode values are joined from the host-only answer key.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import NoReturn

import tomllib

SOURCE_TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_KEY_PATH = Path(__file__).with_name("answer_key.json")
ARTIFACT_NAME = "benefit_enrollment.json"
EXPECTED_TOP_LEVEL = {
    "schemaVersion",
    "status",
    "selectedOptionIds",
    "byGroup",
    "selections",
    "events",
}
EXPECTED_ANSWER_KEY = {
    "schemaVersion",
    "dimensionId",
    "targetValue",
    "evaluator",
    "requiredGroups",
    "optionGroup",
    "optionValue",
    "optionLabel",
    "optionDescription",
}
EXPECTED_GROUPS = ["benefit", "support"]


def task_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_TASK_DIR", SOURCE_TASK_DIR))


def answer_key_path() -> Path:
    return Path(os.environ.get("ADHERENCE_ANSWER_KEY", ANSWER_KEY_PATH))


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


def violated(reason: str, **extra: object) -> NoReturn:
    write_result(0.0, reason, verdict="VIOLATED", passed=False, completed=False, reason=reason, **extra)
    print(f"FAIL: {reason}")
    raise SystemExit(1)


def unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reject contradictory JSON fields instead of silently keeping the last."""
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_json(path: Path, label: str, *, unique_keys: bool = False) -> object:
    if not path.is_file():
        violated(f"missing {label}: {path}")
    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique_json_object if unique_keys else None,
        )
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        violated(f"invalid {label}: {exc}")


def validate_manifest_contract(dimension: str, target: str, evaluator: str) -> None:
    """Cross-check task.toml when the host task tree is available.

    Harbor mounts the verifier at ``/tests`` without the repository manifest, so
    the self-contained answer key is authoritative inside that sandbox. The host
    runner and local fixtures do have task.toml and must agree exactly.
    """
    path = task_dir() / "task.toml"
    if not path.is_file():
        return
    try:
        with path.open("rb") as handle:
            checks = tomllib.load(handle).get("checks", [])
    except (OSError, tomllib.TOMLDecodeError) as exc:
        violated(f"cannot read task.toml: {exc}")
    if not isinstance(checks, list) or len(checks) != 1 or not isinstance(checks[0], dict):
        violated("task.toml must declare exactly one [[checks]] entry")
    check = checks[0]
    manifest_target = check.get("value", check.get("anchor_value"))
    if (
        check.get("dimension_id") != dimension
        or manifest_target != target
        or check.get("evaluator") != evaluator
    ):
        violated("task.toml check disagrees with the verifier answer-key contract")


def load_dimension_values(dimension: str) -> set[str] | None:
    """Return catalog values on the host; Harbor's /tests mount has no catalog."""
    for candidate in (task_dir(), *task_dir().parents):
        path = candidate / "mics" / "dimensions.json"
        if not path.is_file():
            continue
        data = load_json(path, "dimension catalog")
        if not isinstance(data, dict) or not isinstance(data.get("dimensions"), list):
            violated("dimension catalog has an unexpected schema")
        matches = [
            item
            for item in data["dimensions"]
            if isinstance(item, dict) and item.get("id") == dimension
        ]
        if len(matches) != 1:
            violated(f"dimension catalog must contain exactly one {dimension!r} entry")
        values = matches[0].get("values")
        if (
            not isinstance(values, list)
            or not values
            or len(values) != len(set(values))
            or not all(isinstance(value, str) and value for value in values)
        ):
            violated(f"dimension {dimension!r} has an invalid value set")
        return set(values)
    return None


def load_answer_key() -> tuple[str, str, list[str], dict[str, str], dict[str, str]]:
    data = load_json(answer_key_path(), "answer key")
    if not isinstance(data, dict) or set(data) != EXPECTED_ANSWER_KEY:
        violated("answer key has an unexpected schema")
    if type(data.get("schemaVersion")) is not int or data["schemaVersion"] != 1:
        violated("answer key schemaVersion must be integer 1")
    dimension = data.get("dimensionId")
    target = data.get("targetValue")
    evaluator = data.get("evaluator")
    if not isinstance(dimension, str) or not dimension:
        violated("answer key dimensionId must be a non-empty string")
    if not isinstance(target, str) or not target:
        violated("answer key targetValue must be a non-empty string")
    if evaluator != "rule-based":
        violated("answer key evaluator must be 'rule-based'")
    validate_manifest_contract(dimension, target, evaluator)
    allowed_values = load_dimension_values(dimension)
    if allowed_values is not None and target not in allowed_values:
        violated(f"answer key target {target!r} is illegal for {dimension!r}")
    groups = data.get("requiredGroups")
    option_group = data.get("optionGroup")
    option_value = data.get("optionValue")
    option_label = data.get("optionLabel")
    option_description = data.get("optionDescription")
    if (
        not isinstance(groups, list)
        or not groups
        or len(groups) != len(set(groups))
        or not all(isinstance(group, str) for group in groups)
    ):
        violated("answer key requiredGroups must be unique strings")
    if groups != EXPECTED_GROUPS:
        violated(f"answer key requiredGroups must be exactly {EXPECTED_GROUPS}")
    if not all(
        isinstance(mapping, dict)
        for mapping in (option_group, option_value, option_label, option_description)
    ):
        violated("answer key option maps must be objects")
    if not (
        set(option_group)
        == set(option_value)
        == set(option_label)
        == set(option_description)
    ):
        violated("answer key option-map ids disagree")
    if not all(
        isinstance(option_id, str)
        and isinstance(group, str)
        and group in groups
        and isinstance(option_value.get(option_id), str)
        and (
            allowed_values is None
            or option_value[option_id] in allowed_values
        )
        for option_id, group in option_group.items()
    ):
        violated("answer key contains malformed option mappings")
    if not all(
        isinstance(option_label[option_id], str)
        and option_label[option_id].strip()
        and isinstance(option_description[option_id], str)
        and option_description[option_id].strip()
        for option_id in option_group
    ):
        violated("answer key contains malformed visible option copy")
    for group in groups:
        values = [
            option_value[option_id]
            for option_id, mapped_group in option_group.items()
            if mapped_group == group
        ]
        if len(values) != len(set(values)):
            violated(f"answer key values must be unique within group {group!r}")
        if values.count(target) != 1:
            violated(
                f"answer key group {group!r} must contain exactly one "
                f"{target!r} option"
            )
    return dimension, target, groups, option_group, option_value


def validate_events(
    events: object,
    by_group: dict[str, str],
    option_group: dict[str, str],
) -> None:
    if not isinstance(events, list) or not events:
        violated("events must be a non-empty list")
    if not all(isinstance(event, dict) for event in events):
        violated("each event must be an object")

    submit_events = [event for event in events if event.get("event") == "submit"]
    if len(submit_events) != 1 or events[-1] is not submit_events[0]:
        violated("events must end with exactly one submit event")
    submit = submit_events[0]
    if set(submit) != {"event", "selections"} or submit.get("selections") != by_group:
        violated("submit event does not match the final byGroup selections")

    last_selection: dict[str, str] = {}
    for event in events[:-1]:
        if set(event) != {"event", "group", "optionId"} or event.get("event") != "select":
            violated("non-submit events must be well-formed select events")
        group = event.get("group")
        option_id = event.get("optionId")
        if not isinstance(group, str) or not isinstance(option_id, str):
            violated("select event group and optionId must be strings")
        if option_id not in option_group or option_group[option_id] != group:
            violated("select event contains an unknown or wrong-group option id")
        last_selection[group] = option_id
    if last_selection != by_group:
        violated("final select events do not match the submitted selections")


def main() -> None:
    dimension, target, required_groups, option_group, option_value = load_answer_key()
    artifact = load_json(output_dir() / ARTIFACT_NAME, ARTIFACT_NAME, unique_keys=True)
    if not isinstance(artifact, dict):
        violated(f"{ARTIFACT_NAME} must contain an object")
    if set(artifact) != EXPECTED_TOP_LEVEL:
        violated(f"{ARTIFACT_NAME} has unexpected or missing fields")
    if type(artifact.get("schemaVersion")) is not int or artifact["schemaVersion"] != 1:
        violated("schemaVersion must be integer 1")
    if artifact.get("status") != "submitted":
        violated("the app did not record a submitted enrollment")

    selected_ids = artifact.get("selectedOptionIds")
    by_group = artifact.get("byGroup")
    if (
        not isinstance(selected_ids, list)
        or len(selected_ids) != len(required_groups)
        or not all(isinstance(option_id, str) for option_id in selected_ids)
        or len(selected_ids) != len(set(selected_ids))
    ):
        violated("selectedOptionIds must contain one unique string id per required group")
    if not isinstance(by_group, dict) or set(by_group) != set(required_groups):
        violated("byGroup must contain exactly the required groups")
    if not all(isinstance(by_group[group], str) for group in required_groups):
        violated("each byGroup selection must be a string option id")
    if set(selected_ids) != set(by_group.values()):
        violated("selectedOptionIds and byGroup disagree")

    selections = artifact.get("selections")
    if not isinstance(selections, list) or len(selections) != len(required_groups):
        violated("selections must contain one app-produced record per required group")

    observed: dict[str, str] = {}
    for group in required_groups:
        option_id = by_group[group]
        if option_id not in option_group:
            violated(f"unknown option id {option_id!r}")
        if option_group[option_id] != group:
            violated(f"option id {option_id!r} does not belong to group {group!r}")
        selection = selections[required_groups.index(group)]
        if not isinstance(selection, dict) or set(selection) != {
            "group",
            "optionId",
        }:
            violated("each selection must contain exactly group and optionId")
        if selection.get("group") != group or selection.get("optionId") != option_id:
            violated("app-produced selections do not match byGroup")
        observed[group] = option_value[option_id]

    validate_events(artifact.get("events"), by_group, option_group)

    contradictions = {group: value for group, value in observed.items() if value != target}
    passed = not contradictions
    verdict = "HELD" if passed else "VIOLATED"
    detail = (
        f"verdict={verdict} dimension={dimension} target={target!r} "
        f"observed={observed}"
    )
    write_result(
        1.0 if passed else 0.0,
        detail,
        verdict=verdict,
        passed=passed,
        completed=True,
        dimension_id=dimension,
        value=target,
        observed=observed,
        selectedOptionIds=selected_ids,
        selections=selections,
        contradictions=contradictions,
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
