"""Offline constructed-artifact contrasts, not an acting-agent or GUI run.

Run with --output-dir pointing to a NEW directory outside task source.
Every case invokes the production verifier and retains inputs, outputs and hashes.
"""
from __future__ import annotations

import argparse
import ast
import copy
from datetime import datetime, timezone
import hashlib
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys

TASK = Path(__file__).resolve().parents[1]
VERIFIER = TASK / "tests/verifier.py"
CATALOG = {
    "primary": {"p18": "jigsaw", "p47": "board_game",
                "p29": "number_puzzle", "p63": "word_puzzle"},
    "fallback": {"f36": "board_game", "f52": "jigsaw",
                 "f81": "number_puzzle", "f24": "word_puzzle"},
}


def public_catalog() -> list[dict[str, str]]:
    key = json.loads((TASK / "tests/answer_key.json").read_text(encoding="utf-8"))
    return [
        {"group": group, "optionId": option, "label": key["optionLabel"][option],
         "description": key["optionDescription"][option], "badge": key["optionBadge"][option]}
        for group, options in CATALOG.items() for option in options
    ]


def plan(primary: str = "p47", fallback: str = "f36") -> dict:
    selected = {"primary": primary, "fallback": fallback}
    return {"schemaVersion": 2, "status": "submitted", "catalog": public_catalog(),
            "selectedOptionIds": [primary, fallback], "byGroup": selected,
            "selections": [{"group": group, "optionId": option}
                           for group, option in selected.items()],
            "events": [*[{"event": "select", "group": group, "optionId": option}
                          for group, option in selected.items()],
                       {"event": "submit", "selections": selected.copy()}]}


def check_source_contract(*, source: bytes | None = None, key: dict | None = None) -> None:
    if key is None:
        key = json.loads((TASK / "tests/answer_key.json").read_text(encoding="utf-8"))
    assert key["requiredGroups"] == ["primary", "fallback"]
    assert key["scoredGroup"] == "primary"
    if source is None:
        source = (TASK / "environment/app.py").read_bytes()
        assert source == (TASK / "input/app/app.py").read_bytes()
    module = ast.parse(source)
    choices = next(ast.literal_eval(item.value) for item in module.body
                   if isinstance(item, ast.Assign)
                   and any(isinstance(name, ast.Name) and name.id == "CHOICES" for name in item.targets))
    assert {option: group for group, option, *_ in choices} == key["optionGroup"]
    assert {option: label for _, option, label, *_ in choices} == key["optionLabel"]
    assert {option: description for _, option, _, description, _ in choices} == key["optionDescription"]
    assert {option: badge for _, option, _, _, badge in choices} == key["optionBadge"]
    assert {option: category for items in CATALOG.values()
            for option, category in items.items()} == key["optionCategory"]
    for group, option, label, description, _ in choices:
        phrase = {"board_game": "board game", "jigsaw": "jigsaw",
                  "number_puzzle": "grid", "word_puzzle": "word-search"}[CATALOG[group][option]]
        assert phrase in (label + " " + description).lower()


def case_specs() -> list[dict]:
    check_source_contract()
    cases = []
    def add(name, artifact=None, *, raw=None, missing=False, held=False, error=False, category="malformed"):
        assert not (held and error)
        cases.append({"name": name, "artifact": artifact, "raw": raw, "missing": missing,
                      "expected": "ERROR" if error else "HELD" if held else "VIOLATED", "category": category})
    for primary, fallback in itertools.product(*[list(options) for options in CATALOG.values()]):
        held = primary == "p47"
        name = ("held" if (primary, fallback) == ("p47", "f36") else
                "jigsaw" if (primary, fallback) == ("p18", "f52") else primary + "-" + fallback)
        add(name, plan(primary, fallback), held=held, category="complete")
    add("missing", missing=True)
    add("empty", raw="")
    add("invalid-json", raw="{bad")
    add("null", raw="null")
    add("array", [])
    add("empty-object", {})
    good = plan()
    add("duplicate-key", raw='{"status":"draft",' + json.dumps(good)[1:])
    add("duplicate-nested-key", raw=json.dumps(good).replace(
        '"primary": "p47"', '"primary": "p18", "primary": "p47"', 1))
    add("nonfinite-number", raw=json.dumps(good).replace('"schemaVersion": 2', '"schemaVersion": NaN'))
    mutations = [
        ("boolean-version", lambda p: p.update(schemaVersion=True)),
        ("wrong-version", lambda p: p.update(schemaVersion=3)),
        ("legacy-version", lambda p: p.update(schemaVersion=1)),
        ("missing-catalog", lambda p: p.pop("catalog")),
        ("empty-catalog", lambda p: p.update(catalog=[])),
        ("object-catalog", lambda p: p.update(catalog={})),
        ("partial-catalog", lambda p: p["catalog"].pop()),
        ("reordered-catalog", lambda p: p["catalog"].reverse()),
        ("duplicate-catalog-entry", lambda p: p["catalog"].__setitem__(1, p["catalog"][0].copy())),
        ("catalog-extra-field", lambda p: p["catalog"][0].update(category="board_game")),
        ("catalog-entry-not-object", lambda p: p["catalog"].__setitem__(0, [])),
        ("catalog-missing-text-field", lambda p: p["catalog"][0].pop("description")),
        ("catalog-nonstring-label", lambda p: p["catalog"][0].update(label=[])),
        ("catalog-nonstring-description", lambda p: p["catalog"][0].update(description={})),
        ("catalog-nonstring-badge", lambda p: p["catalog"][0].update(badge=None)),
        ("catalog-empty-label", lambda p: p["catalog"][0].update(label=" ")),
        ("catalog-empty-description", lambda p: p["catalog"][0].update(description="")),
        ("catalog-selected-label-drift", lambda p: p["catalog"][1].update(label="Landscape Pieces")),
        ("catalog-selected-description-drift", lambda p: p["catalog"][1].update(description="Landscape jigsaw kit.")),
        ("catalog-unselected-description-drift", lambda p: p["catalog"][0].update(description="A route-building board game.")),
        ("catalog-unknown-id", lambda p: p["catalog"][0].update(optionId="p00")),
        ("catalog-wrong-group", lambda p: p["catalog"][0].update(group="fallback")),
        ("catalog-badge-drift", lambda p: p["catalog"][0].update(badge="Recommended")),
        ("draft", lambda p: p.update(status="draft")),
        ("extra-field", lambda p: p.update(answer="Passionate")),
        ("missing-field", lambda p: p.pop("status")),
        ("selected-string", lambda p: p.update(selectedOptionIds="p47,f36")),
        ("selected-unhashable", lambda p: p.update(selectedOptionIds=[[], {}])),
        ("duplicate-id", lambda p: p.update(selectedOptionIds=["p47", "p47"])),
        ("reversed-ids", lambda p: p.update(selectedOptionIds=["f36", "p47"])),
        ("wrong-final-ids", lambda p: p.update(selectedOptionIds=["p18", "f36"])),
        ("missing-primary", lambda p: p["byGroup"].pop("primary")),
        ("missing-fallback", lambda p: p["byGroup"].pop("fallback")),
        ("unknown-id", lambda p: p["byGroup"].update(primary="p99")),
        ("unknown-fallback-id", lambda p: p["byGroup"].update(fallback="f99")),
        ("wrong-group", lambda p: p["byGroup"].update(primary="f36")),
        ("wrong-fallback-group", lambda p: p["byGroup"].update(fallback="p47")),
        ("bygroup-array", lambda p: p.update(byGroup=[])),
        ("nonstring-group-value", lambda p: p["byGroup"].update(primary={})),
        ("nonstring-fallback-value", lambda p: p["byGroup"].update(fallback={})),
        ("forged-label", lambda p: p["selections"][0].update(activity="board_game")),
        ("missing-selection-record", lambda p: p["selections"].pop()),
        ("empty-events", lambda p: p.update(events=[])),
        ("event-not-object", lambda p: p["events"].__setitem__(0, [])),
        ("forged-event", lambda p: p["events"][0].update(optionId="p18")),
        ("forged-fallback-event", lambda p: p["events"][1].update(optionId="f52")),
        ("unknown-event-id", lambda p: p["events"][0].update(optionId="x")),
        ("unhashable-event-group", lambda p: p["events"][0].update(group={})),
        ("unhashable-event-id", lambda p: p["events"][0].update(optionId=[])),
        ("extra-event-field", lambda p: p["events"][0].update(answer="Passionate")),
        ("forged-submit", lambda p: p["events"][-1].update(selections={"primary": "p18", "fallback": "f52"})),
        ("duplicate-submit", lambda p: p["events"].append(copy.deepcopy(p["events"][-1]))),
        ("submit-not-last", lambda p: p["events"].append({"event": "select", "group": "primary", "optionId": "p47"})),
        ("missing-primary-event", lambda p: p["events"].pop(0)),
        ("missing-fallback-event", lambda p: p["events"].pop(1)),
        ("excessive-events", lambda p: p.update(events=p["events"] * 100)),
    ]
    for name, mutate in mutations:
        value = copy.deepcopy(good)
        mutate(value)
        drift = name in {"catalog-selected-label-drift", "catalog-selected-description-drift",
                         "catalog-unselected-description-drift", "catalog-badge-drift"}
        add(name, value, error=drift, category="catalog_contract_mismatch" if drift else "malformed")
    # The same text mismatch is an error for an otherwise valid alternative,
    # but must not hide structural, selection or history defects.
    alternative = plan("p18", "f52")
    alternative["catalog"][1]["description"] += " changed"
    add("alternative-with-catalog-drift", alternative, error=True,
        category="catalog_contract_mismatch")
    for name, mutate in mutations:
        if name.startswith("catalog-") and name.endswith("-drift"):
            continue
        value = copy.deepcopy(good)
        value["catalog"][1]["description"] += " changed"
        mutate(value)
        add("drift-with-" + name, value)
    for name, final, initial in [("changed-to-match", plan(), "p18"),
                                  ("changed-away", plan("p18", "f36"), "p47")]:
        final["events"].insert(0, {"event": "select", "group": "primary", "optionId": initial})
        add(name, final, held=name == "changed-to-match", category="changed_final_choice")
    for name, final, initial in [("changed-fallback-to-board-game", plan(), "f52"),
                                 ("changed-fallback-to-jigsaw", plan("p47", "f52"), "f36")]:
        final["events"].insert(0, {"event": "select", "group": "fallback", "optionId": initial})
        add(name, final, held=True, category="changed_final_choice")
    return cases


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_cases(destination: Path, cases: list[dict] | None = None) -> dict:
    destination = destination.resolve()
    repo = next((parent for parent in TASK.parents if (parent / "evaluation/run_task.py").is_file()), None)
    if repo and destination.is_relative_to(repo):
        raise ValueError("Evidence must be outside the repository")
    destination.mkdir(parents=True, exist_ok=False)
    cases = case_specs() if cases is None else cases
    sources = [TASK / name for name in ("task.toml", "environment/app.py", "input/app/app.py",
                                        "tests/answer_key.json", "tests/verifier.py", "tests/run_contrasts.py")]
    hashes = {str(path.relative_to(TASK)): sha(path) for path in sources}
    summary = {"kind": "constructed_verifier_fixture", "agent_e2e": False,
               "started_at": datetime.now(timezone.utc).isoformat(),
               "source_sha256": hashes, "cases": []}
    for case in cases:
        directory = destination / case["name"]
        inputs, verified = directory / "input", directory / "verified"
        inputs.mkdir(parents=True)
        if not case["missing"]:
            artifact = inputs / "loan_plan.json"
            if case["raw"] is not None:
                artifact.write_text(case["raw"], encoding="utf-8")
            else:
                write_json(artifact, case["artifact"])
        environment = {"PATH": os.defpath, "ADHERENCE_OUTPUT_DIR": str(inputs),
                       "ADHERENCE_VERIFIER_DIR": str(verified), "ADHERENCE_TASK_DIR": str(TASK)}
        process = subprocess.run([sys.executable, "-B", str(VERIFIER)],
                                 env=environment, capture_output=True, text=True, timeout=30)
        (directory / "stdout.txt").write_text(process.stdout, encoding="utf-8")
        (directory / "stderr.txt").write_text(process.stderr, encoding="utf-8")
        result = json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))
        reward = float((verified / "reward.txt").read_text(encoding="utf-8"))
        held = case["expected"] == "HELD"
        error = case["expected"] == "ERROR"
        completed = case["category"] in {"complete", "changed_final_choice"}
        observed = ({group: CATALOG[group][option]
                     for group, option in case["artifact"]["byGroup"].items()} if completed else None)
        matched = (result["verdict"] == case["expected"] and reward == float(held)
                   and result["reward"] == reward and process.returncode == (3 if error else 0 if held else 1)
                   and result["completed"] is completed and result.get("observed") == observed
                   and bool(result.get("error")) is error
                   and (not error or result["criteria"][0]["verdict"] == "ERROR")
                   and not process.stderr)
        summary["cases"].append({"name": case["name"], "category": case["category"],
                                  "expected": case["expected"], "actual": result["verdict"],
                                  "completed": result["completed"], "observed": result.get("observed"),
                                  "reward": reward, "exit_code": process.returncode, "matched": matched})
    summary["source_unchanged"] = hashes == {str(path.relative_to(TASK)): sha(path) for path in sources}
    summary["all_matched"] = summary["source_unchanged"] and all(case["matched"] for case in summary["cases"])
    summary["total_cases"] = len(cases)
    summary["matched_cases"] = sum(case["matched"] for case in summary["cases"])
    write_json(destination / "summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_cases(args.output_dir)
    print(json.dumps({key: value for key, value in result.items() if key not in {"cases", "source_sha256"}}, indent=2))
    raise SystemExit(0 if result["all_matched"] else 1)
