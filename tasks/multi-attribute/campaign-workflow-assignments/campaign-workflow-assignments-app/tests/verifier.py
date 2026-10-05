"""Strict Linux App verifier with exact visible-source/host-key binding."""
import ast
import hashlib
import json
import os
import re
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent
APP_SOURCE = TESTS / "choiceapp.py"
KEY = TESTS / "answer_key.yaml"
PERSONA = "hf-4386921459"
LABELS = ("trello", "persuasion")
EXPECTED_TRUE = {
    "trello": frozenset({"p01", "p04", "p05", "p07"}),
    "persuasion": frozenset({"p01", "p03", "p06", "p07"}),
}
CHECKS = (("tool_trello=Power user", "trello"), ("skill_persuasion=Advanced", "persuasion"))
MAX_POINTS = len(CHECKS)
MAX_ARTIFACT_BYTES = 100_000


class ContractError(ValueError):
    pass


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write(reward: float, detail: str, extra: dict) -> None:
    verifier_dir().mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (verifier_dir() / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (verifier_dir() / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fail(message: str, *, infra: bool = False) -> None:
    extra = {"checks": [], "points": 0, "max_points": MAX_POINTS}
    if infra:
        extra["error"] = message
    write(0.0, message, extra)
    print("FAIL:", message)
    raise SystemExit(1)


def load_catalog(app_path: Path = APP_SOURCE, key_path: Path = KEY) -> dict:
    try:
        tree = ast.parse(app_path.read_text(encoding="utf-8"))
        raw = json.loads(key_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load app/key: {exc}") from exc
    assignments = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "MENU"
                                                 for target in node.targets):
            try:
                assignments.append(ast.literal_eval(node.value))
            except (ValueError, TypeError) as exc:
                raise ContractError("MENU must be a literal catalog") from exc
    if len(assignments) != 1:
        raise ContractError("app must contain exactly one MENU catalog")
    rows = assignments[0]
    if not isinstance(rows, list) or len(rows) != 8:
        raise ContractError("MENU must contain exactly eight rows")
    if any(not isinstance(row, tuple) or len(row) != 5 or
           any(not isinstance(value, str) or not value.strip() for value in row) for row in rows):
        raise ContractError("MENU rows must be five non-empty strings")
    if len({row[0] for row in rows}) != 8:
        raise ContractError("MENU ids must be unique")
    if len({row[2] for row in rows}) != 8:
        raise ContractError("MENU names must be unique")
    visible = {row[0]: (row[2], row[3]) for row in rows}
    if not isinstance(raw, dict) or set(raw) != {"items"} or not isinstance(raw["items"], dict):
        raise ContractError("answer key must contain exactly items")
    items = raw["items"]
    if set(items) != set(visible) or len(items) != 8:
        raise ContractError("app/key id coverage mismatch")
    required = {"name", "text_sha256", *LABELS}
    for oid, keyed in items.items():
        if not isinstance(oid, str) or not isinstance(keyed, dict) or set(keyed) != required:
            raise ContractError(f"malformed answer-key row {oid!r}")
        if not isinstance(keyed["name"], str) or not keyed["name"].strip():
            raise ContractError(f"invalid name for {oid!r}")
        if not isinstance(keyed["text_sha256"], str) or re.fullmatch(r"[0-9a-f]{64}", keyed["text_sha256"]) is None:
            raise ContractError(f"invalid text hash for {oid!r}")
        if any(type(keyed[label]) is not bool for label in LABELS):
            raise ContractError(f"non-boolean label for {oid!r}")
        name, text = visible[oid]
        if keyed["name"] != name or keyed["text_sha256"] != hashlib.sha256(text.encode()).hexdigest():
            raise ContractError(f"visible name/text drift for {oid!r}")
    for label, expected in EXPECTED_TRUE.items():
        if {oid for oid, keyed in items.items() if keyed[label]} != expected:
            raise ContractError(f"answer-key semantic labels drifted for {label!r}")
    return items


def load_picks(items: dict) -> list[str]:
    path = output_dir() / "selection.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        if path.stat().st_size > MAX_ARTIFACT_BYTES:
            fail("selection.json is too large")
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid selection.json: {exc}")
    if not isinstance(artifact, dict) or set(artifact) != {"persona", "selectedPlans"}:
        fail("artifact must contain exactly persona and selectedPlans")
    if artifact["persona"] != PERSONA:
        fail(f"artifact persona must equal {PERSONA!r}")
    rows = artifact["selectedPlans"]
    if not isinstance(rows, list):
        fail("selectedPlans must be a list")
    if len(rows) != 2:
        fail(f"submission has {len(rows)} rows; exactly two are required")
    picks = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "name"}:
            fail("each selected plan must contain exactly id and name")
        oid, name = row["id"], row["name"]
        if not isinstance(oid, str) or not isinstance(name, str):
            fail("selected plan id/name must be strings")
        if oid not in items or name != items[oid]["name"]:
            fail("submission contains an unknown id or forged name")
        picks.append(oid)
    if len(set(picks)) != len(picks):
        fail("submission contains duplicate ids")
    return picks


def main() -> None:
    try:
        items = load_catalog()
    except ContractError as exc:
        fail(str(exc), infra=True)
    picks = load_picks(items)
    results = []
    for name, label in CHECKS:
        offside = [oid for oid in picks if items[oid][label] is not True]
        held = not offside
        results.append({"evaluator": name, "label": label,
                        "verdict": "HELD" if held else "VIOLATED", "passed": held,
                        "offside_picks": offside})
    points = sum(result["passed"] for result in results)
    detail = f"persona={PERSONA} score {points}/{MAX_POINTS}: " + ", ".join(
        f"{result['evaluator']}={result['verdict']}" for result in results
    )
    write(float(points), detail, {"persona": PERSONA, "checks": results,
          "score": f"{points}/{MAX_POINTS}", "points": points,
          "max_points": MAX_POINTS, "passed_count": points,
          "total_checks": MAX_POINTS, "picks": picks})
    print(detail)


if __name__ == "__main__":
    main()
