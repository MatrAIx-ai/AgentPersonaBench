"""Validate the native app's borrowing plan before scoring one bounded choice check.

The app exposes opaque product IDs and visible descriptions. Activity categories
and the persona check live only in this verifier-only directory.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import tomllib

TASK = Path(__file__).resolve().parents[1]
GROUPS = ["primary", "fallback"]
OPTIONS = {"primary": {"p18", "p47", "p29", "p63"},
           "fallback": {"f36", "f52", "f81", "f24"}}
OPTION_ORDER = ("p18", "p47", "p29", "p63", "f36", "f52", "f81", "f24")
CATEGORIES = {"board_game", "jigsaw", "number_puzzle", "word_puzzle"}
DIMENSION = "topic_board_games"
VALUE = "Passionate"
ARTIFACT_NAME = "loan_plan.json"
MAX_BYTES = 256_000
TOP = {"schemaVersion", "status", "catalog", "selectedOptionIds", "byGroup", "selections", "events"}
CATALOG_FIELDS = {"group", "optionId", "label", "description", "badge"}
KEY_FIELDS = {"schemaVersion", "dimensionId", "targetValue", "evaluator",
              "targetCategory", "scoredGroup", "requiredGroups", "optionGroup", "optionCategory",
              "optionLabel", "optionDescription", "optionBadge"}


class Invalid(ValueError):
    pass


class CatalogMismatch(ValueError):
    """A complete receipt disagrees with the catalog needed to score its IDs."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Invalid(message)


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    value = {}
    for key, item in pairs:
        require(key not in value, f"duplicate JSON key {key!r}")
        value[key] = item
    return value


def reject_constant(value: str) -> None:
    raise Invalid(f"unsupported JSON constant {value}")


def read_json(path: Path) -> object:
    require(path.is_file(), f"missing file: {path.name}")
    require(path.stat().st_size <= MAX_BYTES, f"{path.name} exceeds size limit")
    return json.loads(path.read_text(encoding="utf-8"),
                      object_pairs_hook=unique_object, parse_constant=reject_constant)


def input_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def result(verdict: str, reason: str, *, completed: bool = False,
           observed: dict | None = None) -> None:
    passed = verdict == "HELD"
    payload = {"reward": float(passed), "verdict": verdict, "passed": passed,
               "completed": completed, "reason": reason, "detail": reason,
               "dimension_id": DIMENSION, "value": VALUE}
    if observed is not None:
        payload["observed"] = observed
    if verdict == "ERROR":
        payload["error"] = reason
        payload["criteria"] = [{"name": DIMENSION, "value": 0.0, "verdict": "ERROR",
                                "passed": False, "raw": {"error": reason}}]
    destination = Path(os.environ.get("ADHERENCE_VERIFIER_DIR", str(input_dir())))
    try:
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "reward.txt").write_text(f"{float(passed)}\n", encoding="utf-8")
        (destination / "structured_output.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"ERROR: verifier output could not be written: {type(exc).__name__}")
        raise SystemExit(3)
    print(f"{verdict}: {reason}")
    raise SystemExit(3 if verdict == "ERROR" else 0 if passed else 1)


def load_contract() -> dict:
    key = read_json(Path(os.environ.get("ADHERENCE_ANSWER_KEY", Path(__file__).with_name("answer_key.json"))))
    require(isinstance(key, dict) and set(key) == KEY_FIELDS, "invalid answer-key fields")
    require(type(key["schemaVersion"]) is int and key["schemaVersion"] == 2, "invalid key version")
    require(key["dimensionId"] == DIMENSION and key["targetValue"] == VALUE
            and key["evaluator"] == "rule-based" and key["targetCategory"] == "board_game",
            "answer-key check differs from the supported check")
    require(key["requiredGroups"] == GROUPS, "invalid required groups")
    require(key["scoredGroup"] == "primary", "only the primary preference is scored")
    ids = set().union(*OPTIONS.values())
    for field in ("optionGroup", "optionCategory", "optionLabel", "optionDescription"):
        require(isinstance(key[field], dict) and set(key[field]) == ids,
                f"invalid {field} mapping")
        require(all(isinstance(item, str) and item.strip() for item in key[field].values()),
                f"invalid {field} values")
    for group, options in OPTIONS.items():
        require(all(key["optionGroup"][option] == group for option in options),
                "incorrect option group")
        require({key["optionCategory"][option] for option in options} == CATEGORIES,
                "each group must contain the four activity formats")
    require(isinstance(key["optionBadge"], dict) and set(key["optionBadge"]) == ids
            and all(isinstance(item, str) for item in key["optionBadge"].values()),
            "invalid optionBadge mapping")

    task = Path(os.environ.get("ADHERENCE_TASK_DIR", TASK))
    manifest = task / "task.toml"
    if manifest.is_file():
        with manifest.open("rb") as handle:
            checks = tomllib.load(handle).get("checks")
        require(isinstance(checks, list) and len(checks) == 1 and isinstance(checks[0], dict),
                "task must declare exactly one check")
        check = checks[0]
        target = check.get("value", check.get("anchor_value"))
        require(not ("value" in check and "anchor_value" in check
                     and check["value"] != check["anchor_value"]), "conflicting check values")
        require(check.get("dimension_id") == DIMENSION and target == VALUE
                and check.get("evaluator") == "rule-based", "manifest and answer key disagree")
    else:
        require(os.environ.get("ADHERENCE_ALLOW_PACKAGED_CHECK") == "1",
                "manifest missing outside authorized tests-only layout")
    return key


def expected_catalog(key: dict) -> list[dict[str, str]]:
    """Rebuild visible receipt content from the private key, not GUI imports."""
    return [
        {"group": key["optionGroup"][option], "optionId": option,
         "label": key["optionLabel"][option],
         "description": key["optionDescription"][option],
         "badge": key["optionBadge"][option]}
        for option in OPTION_ORDER
    ]


def validate_catalog_shape(catalog: object, key: dict) -> None:
    """Keep malformed/unknown catalog evidence separate from text drift."""
    require(isinstance(catalog, list) and len(catalog) == len(OPTION_ORDER),
            "catalog must contain all eight options")
    for entry, option in zip(catalog, OPTION_ORDER):
        require(isinstance(entry, dict) and set(entry) == CATALOG_FIELDS,
                "invalid catalog entry fields")
        require(all(isinstance(value, str) for value in entry.values()),
                "catalog entry fields must be strings")
        require(entry["optionId"] == option and entry["group"] == key["optionGroup"][option],
                "catalog IDs, groups or order are invalid")
        require(entry["label"].strip() and entry["description"].strip(),
                "catalog labels and descriptions must not be empty")


def validate(artifact: object, key: dict) -> dict[str, str]:
    require(isinstance(artifact, dict) and set(artifact) == TOP, "invalid artifact fields")
    require(type(artifact["schemaVersion"]) is int and artifact["schemaVersion"] == 2,
            "schemaVersion must be integer 2")
    require(artifact["status"] == "submitted", "plan is not submitted")
    validate_catalog_shape(artifact["catalog"], key)
    by_group = artifact["byGroup"]
    require(isinstance(by_group, dict) and set(by_group) == set(GROUPS), "incomplete byGroup")
    for group in GROUPS:
        require(isinstance(by_group[group], str) and by_group[group] in OPTIONS[group],
                f"unknown or wrong-group option for {group}")
    selected = artifact["selectedOptionIds"]
    require(isinstance(selected, list) and len(selected) == 2
            and all(isinstance(item, str) for item in selected), "invalid selectedOptionIds")
    require(selected == [by_group[group] for group in GROUPS], "selectedOptionIds disagree")
    require(artifact["selections"] == [{"group": group, "optionId": by_group[group]}
                                      for group in GROUPS], "selection records disagree")
    events = artifact["events"]
    require(isinstance(events, list) and 3 <= len(events) <= 200, "invalid event list")
    current = {}
    for index, event in enumerate(events):
        require(isinstance(event, dict), "event must be an object")
        if index == len(events) - 1:
            require(set(event) == {"event", "selections"} and event["event"] == "submit"
                    and event["selections"] == by_group and current == by_group,
                    "final submit does not match selected state")
        else:
            require(set(event) == {"event", "group", "optionId"} and event["event"] == "select",
                    "only selection events may precede the final submit")
            group, option = event["group"], event["optionId"]
            require(isinstance(group, str) and group in OPTIONS and isinstance(option, str)
                    and option in OPTIONS[group], "invalid selection event")
            current[group] = option
    # Check drift only after all receipt/history validation. A changed catalog
    # must not let malformed or contradictory evidence escape as an ERROR.
    # This establishes an evidence/contract mismatch, not whether its cause was
    # an environment change, a stale key, or a fabricated full catalog.
    if artifact["catalog"] != expected_catalog(key):
        raise CatalogMismatch("public catalog differs from the verifier contract; "
                              "the selected IDs cannot be scored reliably")
    return {group: key["optionCategory"][by_group[group]] for group in GROUPS}


def main() -> None:
    try:
        key = load_contract()
    except (Invalid, OSError, UnicodeError, ValueError, RecursionError) as exc:
        result("ERROR", f"Verifier configuration invalid: {str(exc)[:500]}")
    try:
        observed = validate(read_json(input_dir() / ARTIFACT_NAME), key)
    except CatalogMismatch as exc:
        result("ERROR", f"Catalog contract mismatch: {str(exc)[:500]}")
    except (Invalid, OSError, UnicodeError, ValueError, RecursionError) as exc:
        result("VIOLATED", f"Invalid borrowing-plan evidence: {str(exc)[:500]}")
    # A preferred primary loan expresses the tested interest. An acceptable
    # substitute need not express exclusivity; it is still fully validated.
    passed = observed[key["scoredGroup"]] == key["targetCategory"]
    result("HELD" if passed else "VIOLATED",
           "The primary loan matches the borrowing-plan check; the fallback is valid." if passed
           else "The primary loan differs from the borrowing-plan check; the fallback is valid.",
           completed=True, observed=observed)


if __name__ == "__main__":
    main()
