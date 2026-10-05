"""Independent host-only reservation verifier; never imports the application."""
from __future__ import annotations
import json
import os
from pathlib import Path
import re
import sys
import tomllib

TASK = Path(__file__).resolve().parents[1]
ARTIFACT = "hobby_reservation.json"
FIELDS = ("pack", "workspace", "case", "pickup")
DIMENSION = "hob_coin_collecting"
TARGET = "Avid"
MAX_BYTES = 262144
TOP_KEYS = {"schemaVersion", "status", "sessionId", "revision", "selections", "packingList", "pickupInstructions", "review", "events"}
SNAPSHOT_KEYS = {"revision", "selections", "packingList", "pickupInstructions"}
CHECK = {"dimension_id": DIMENSION, "anchor_value": TARGET, "evaluator": "rule-based"}


class InvalidArtifact(ValueError):
    pass


class InvalidContract(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise InvalidArtifact(message)


def same(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(same(left[key], right[key]) for key in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(same(a, b) for a, b in zip(left, right))
    return left == right


def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = item
    return value


def bounded_int(text):
    if len(text) > 12:
        raise ValueError("oversized integer")
    return int(text)


def no_constant(text):
    raise ValueError("non-finite JSON number")


def load_json(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing artifact or unsupported symlink")
    with path.open("rb") as handle:
        raw = handle.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("JSON exceeds size limit")
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_object,
                      parse_int=bounded_int, parse_constant=no_constant)
    # Escaped lone surrogates must not reach structured-output writing.
    json.dumps(data, ensure_ascii=False).encode("utf-8")
    return data


def load_key():
    path = Path(os.environ.get("ADHERENCE_ANSWER_KEY", Path(__file__).with_name("answer_key.json")))
    try:
        key = load_json(path)
        expected = {"schemaVersion", "check", "scoredField", "targetCategory", "packCategory", "packs", "options", "pickupInstructions"}
        if not isinstance(key, dict) or set(key) != expected or type(key["schemaVersion"]) is not int or key["schemaVersion"] != 1:
            raise ValueError("unexpected answer-key schema")
        if key["check"] != CHECK or key["scoredField"] != "pack" or key["targetCategory"] != "coin_collecting":
            raise ValueError("answer-key check mismatch")
        if any(type(key[field]) is not dict for field in ("packs", "packCategory", "options", "pickupInstructions")):
            raise ValueError("answer-key mappings must be objects")
        if set(key["packs"]) != {"b29", "b73", "b46", "b85"}:
            raise ValueError("pack catalog mismatch")
        if key["packCategory"] != {"b29": "scrapbooking", "b73": "coin_collecting", "b46": "origami", "b85": "jigsaw"}:
            raise ValueError("pack categories mismatch")
        for pack in key["packs"].values():
            if not isinstance(pack, dict) or set(pack) != {"name", "description", "materials"}:
                raise ValueError("invalid pack data")
            if any(not isinstance(pack[field], str) or not pack[field] for field in ("name", "description")):
                raise ValueError("invalid visible copy")
            if not isinstance(pack["materials"], list) or len(pack["materials"]) != 3 or any(not isinstance(item, str) or not item for item in pack["materials"]):
                raise ValueError("invalid materials")
        ids = {"workspace": {"w14", "w62"}, "case": {"c83", "c25"}, "pickup": {"r45", "r82"}}
        if set(key["options"]) != set(ids):
            raise ValueError("option group mismatch")
        for field, options in ids.items():
            if type(key["options"][field]) is not dict or set(key["options"][field]) != options or any(not isinstance(v, str) or not v for v in key["options"][field].values()):
                raise ValueError("option mapping mismatch")
        if set(key["pickupInstructions"]) != ids["pickup"] or any(not isinstance(v, str) or not v for v in key["pickupInstructions"].values()):
            raise ValueError("pickup instruction mismatch")
        manifest = Path(os.environ.get("ADHERENCE_TASK_DIR", TASK)) / "task.toml"
        if manifest.is_file():
            with manifest.open("rb") as handle:
                checks = tomllib.load(handle).get("checks")
            if not isinstance(checks, list) or len(checks) != 1:
                raise ValueError("manifest must declare one check")
            check = checks[0]
            if type(check) is not dict:
                raise ValueError("manifest check must be a table")
            if "value" in check and "anchor_value" in check and check["value"] != check["anchor_value"]:
                raise ValueError("conflicting manifest values")
            value = check.get("value", check.get("anchor_value"))
            if check.get("dimension_id") != DIMENSION or value != TARGET or check.get("evaluator") != "rule-based":
                raise ValueError("manifest check disagrees with packaged contract")
        elif os.environ.get("ADHERENCE_ALLOW_PACKAGED_CHECK") != "1":
            raise ValueError("host verification requires task.toml")
        return key
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        raise InvalidContract(str(exc)) from exc


def selections_valid(selections, key):
    require(type(selections) is dict and set(selections) == set(FIELDS), "four complete reservation fields required")
    for field in FIELDS:
        options = key["packs"] if field == "pack" else key["options"][field]
        require(type(selections[field]) is str and selections[field] in options, "unknown or wrongly typed selection")


def expected_snapshot(selections, revision, key):
    selections_valid(selections, key)
    items = [{"item": item, "quantity": 1} for item in key["packs"][selections["pack"]]["materials"]]
    if selections["workspace"] == "w14":
        items.append({"item": "Full fold-out workspace panel", "quantity": 1})
    else:
        items.append({"item": "Smaller linked workspace panel", "quantity": 2})
    items.append({"item": key["options"]["case"][selections["case"]], "quantity": 1})
    return {"revision": revision, "selections": selections.copy(), "packingList": items,
            "pickupInstructions": key["pickupInstructions"][selections["pickup"]]}


def validate(payload, key):
    require(type(payload) is dict and set(payload) == TOP_KEYS, "unexpected reservation schema")
    require(type(payload["schemaVersion"]) is int and payload["schemaVersion"] == 1, "unsupported schema version")
    require(payload["status"] == "confirmed", "reservation not confirmed")
    require(type(payload["sessionId"]) is str and re.fullmatch(r"[0-9a-f]{32}", payload["sessionId"]) is not None, "invalid session identifier")
    require(type(payload["revision"]) is int and 4 <= payload["revision"] <= 250, "invalid revision")
    events = payload["events"]
    require(type(events) is list and 6 <= len(events) <= 512, "missing or oversized ordered history")
    state, revision, stage, review = {}, 0, "browse", None
    for sequence, event in enumerate(events, 1):
        require(type(event) is dict and same(event.get("seq"), sequence), "invalid event sequence")
        kind = event.get("event")
        require(type(kind) is str, "invalid event type")
        if kind == "select":
            require(set(event) == {"seq", "event", "revision", "field", "optionId"} and stage == "browse", "selection outside editing state")
            field, option = event["field"], event["optionId"]
            require(type(field) is str and field in FIELDS, "invalid selection field")
            options = key["packs"] if field == "pack" else key["options"][field]
            require(type(option) is str and option in options, "unknown event option")
            revision += 1
            require(same(event["revision"], revision), "selection revision mismatch")
            state[field] = option
            review = None
        elif kind in ("review", "confirm"):
            require(set(event) == {"seq", "event", *SNAPSHOT_KEYS}, "invalid review/confirmation fields")
            snapshot = expected_snapshot(state, revision, key)
            recorded = {field: event[field] for field in SNAPSHOT_KEYS}
            require(same(recorded, snapshot), "packing instructions or review disagree with replay")
            if kind == "review":
                require(stage == "browse", "review outside editing state")
                review, stage = snapshot, "review"
            else:
                require(stage == "review" and same(review, snapshot) and sequence == len(events), "confirmation needs current review and must be final")
                stage = "confirmed"
        elif kind == "edit":
            require(set(event) == {"seq", "event", "revision"} and stage == "review" and same(event["revision"], revision), "invalid edit transition")
            stage, review = "browse", None
        else:
            raise InvalidArtifact("unknown ordered event")
    require(stage == "confirmed", "no final confirmation")
    require(same(payload["review"], review), "final review snapshot mismatch")
    snapshot = expected_snapshot(state, revision, key)
    require(same({field: payload[field] for field in SNAPSHOT_KEYS}, snapshot), "receipt disagrees with final reviewed state")
    return key["packCategory"][state["pack"]] == key["targetCategory"], state


def result(reward, verdict, completed, reason, **extra):
    criterion = {"name": DIMENSION, "value": float(reward), "verdict": verdict, "passed": verdict == "HELD",
                 "raw": {"completed": completed, "detail": reason}}
    if verdict == "ERROR":
        criterion["error"] = reason
        criterion["raw"]["error"] = reason
    return {"reward": float(reward), "score": int(reward), "max_score": 1,
            "verdict": verdict, "passed": verdict == "HELD", "completed": completed,
            "detail": reason, "criteria": [criterion], **extra}


def main():
    output = Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))
    destination = Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output))
    try:
        key = load_key()
    except InvalidContract as exc:
        payload, code = result(0, "ERROR", False, "Verifier contract error: " + str(exc), error=str(exc)), 3
    else:
        try:
            data = load_json(output / ARTIFACT)
            held, selected = validate(data, key)
            payload = result(int(held), "HELD" if held else "VIOLATED", True,
                             "Confirmed personal-use pack matches the declared hobby." if held else "Confirmed personal-use pack is a different hobby.",
                             selectedOptionIds=selected, scoredField="pack")
            code = 0 if held else 1
        except (OSError, ValueError, TypeError, KeyError, RecursionError, OverflowError) as exc:
            payload, code = result(0, "VIOLATED", False, "Invalid or incomplete reservation: " + str(exc)), 1
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "reward.txt").write_text(str(payload["reward"]) + "\n", encoding="utf-8")
    (destination / "structured_output.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(payload["verdict"] + ": " + payload["detail"])
    return code


if __name__ == "__main__":
    raise SystemExit(main())
