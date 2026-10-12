"""Write auditable OFFLINE app-verifier contrast evidence, not GUI or agent E2E trials."""
from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import tomllib

import ast

TASK_DIR = Path(__file__).resolve().parents[1]
VERIFIER = Path(__file__).with_name("verifier.py")
ARTIFACT_NAME = "benefit_enrollment.json"
SURFACE = "app"
DIMENSION = "lstyle_commute_mode"
TARGET = "Public transit"
# Independent expectations tied to the visible application choices.
EXPECTED_VALUES = {
    "benefit": {"b12": "Car", "b44": "Bike", "b37": TARGET, "b25": "Rideshare"},
    "support": {"s18": "Rideshare", "s23": TARGET, "s31": "Car", "s46": "Bike"},
}
VISIBLE_MODE_WORDS = {
    "Car": ("parking", "garage"),
    TARGET: ("bus", "rail", "service"),
    "Bike": ("bike", "bicycle"),
    "Rideshare": ("shared-ride",),
}


def source_paths() -> list[Path]:
    return [TASK_DIR / name for name in (
        "task.toml", "persona.yaml", "instruction.md", "input/app/app.py",
        "environment/app.py", "environment/Dockerfile", "environment/start-app.sh",
        "environment/chromium-policy.json", "environment/terminal-disabled.desktop",
        "solution/solve.sh", "tests/test.sh", "tests/verifier.py",
        "tests/answer_key.json", "tests/run_contrasts.py",
    )]


def load_contract() -> dict[str, dict[str, str]]:
    key = json.loads((TASK_DIR / "tests/answer_key.json").read_text(encoding="utf-8"))
    manifest = tomllib.loads((TASK_DIR / "task.toml").read_text(encoding="utf-8"))
    checks = manifest.get("checks", [])
    if len(checks) != 1 or any(checks[0].get(name) != value for name, value in (
        ("dimension_id", DIMENSION), ("value", TARGET), ("evaluator", "rule-based")
    )):
        raise ValueError("The single task check no longer matches the contrast contract")
    if key["requiredGroups"] != list(EXPECTED_VALUES) or key["targetValue"] != TARGET:
        raise ValueError("Answer-key target/groups changed")
    expected_key = {option: value for options in EXPECTED_VALUES.values() for option, value in options.items()}
    if key["optionValue"] != expected_key:
        raise ValueError("Host key disagrees with independently pinned option semantics")
    source = TASK_DIR / "environment/app.py"
    if source.read_bytes() != (TASK_DIR / "input/app/app.py").read_bytes():
        raise ValueError("Packaged app source copies differ")
    choices = None
    for statement in ast.parse(source.read_text(encoding="utf-8")).body:
        if isinstance(statement, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "CHOICES" for target in statement.targets
        ):
            choices = ast.literal_eval(statement.value)
            break
    if choices is None:
        raise ValueError("Cannot locate literal application choices")
    if key["optionGroup"] != {option: group for group, option, *_ in choices}:
        raise ValueError("Application groups and host key differ")
    if key["optionLabel"] != {option: label for _, option, label, _, _ in choices}:
        raise ValueError("Application labels and host key differ")
    if key["optionDescription"] != {option: detail for _, option, _, detail, _ in choices}:
        raise ValueError("Application descriptions and host key differ")
    for group, option, label, detail, _badge in choices:
        if not any(word in (label + " " + detail).lower()
                   for word in VISIBLE_MODE_WORDS[EXPECTED_VALUES[group][option]]):
            raise ValueError(f"Visible copy no longer supports the pinned mode for {option}")
    return {group: {option: key["optionValue"][option] for option in options}
            for group, options in EXPECTED_VALUES.items()}


def enrollment(selected: dict[str, str]) -> dict:
    """Construct the real app artifact schema; this does not claim GUI interaction."""
    return {
        "schemaVersion": 1,
        "status": "submitted",
        "selectedOptionIds": list(selected.values()),
        "byGroup": selected.copy(),
        "selections": [{"group": group, "optionId": option} for group, option in selected.items()],
        "events": [
            *[{"event": "select", "group": group, "optionId": option}
              for group, option in selected.items()],
            {"event": "submit", "selections": selected.copy()},
        ],
    }


def case_specs() -> list[dict]:
    contract = load_contract()
    groups = list(contract)
    cases = []
    for ids in itertools.product(*(list(options) for options in contract.values())):
        selected = dict(zip(groups, ids, strict=True))
        observed = {group: contract[group][option] for group, option in selected.items()}
        expected = "HELD" if all(value == TARGET for value in observed.values()) else "VIOLATED"
        cases.append(spec(complete_case_id(selected, observed), "behavioral_complete",
                          enrollment(selected), expected=expected, observed=observed))
    selected = {group: next(option for option, value in options.items() if value == TARGET)
                for group, options in contract.items()}
    good = enrollment(selected)
    invalid = "malformed_artifact"
    cases.extend([
        spec("missing-artifact", invalid, missing=True),
        spec("empty-file", invalid, raw=""),
        spec("invalid-json", invalid, raw="{not-json"),
        spec("null-document", invalid, raw="null"),
        spec("array-document", invalid, []),
        spec("empty-object", invalid, {}),
        spec("duplicate-top-level-json-key", invalid,
             raw='{"status": "draft", ' + json.dumps(good)[1:]),
        spec("duplicate-nested-json-key", invalid,
             raw=json.dumps(good).replace(
                 '"byGroup": {"benefit": "b37"',
                 '"byGroup": {"benefit": "b12", "benefit": "b37"', 1)),
    ])
    for group in groups:
        partial = {name: option for name, option in selected.items() if name != group}
        cases.append(spec("missing-" + group, invalid, enrollment(partial)))
    mutations = []
    value = copy.deepcopy(good)
    value["status"] = "draft"
    mutations.append(("unsubmitted-status", value))
    value = copy.deepcopy(good)
    value["schemaVersion"] = True
    mutations.append(("boolean-schema-version", value))
    value = copy.deepcopy(good)
    value["selectedOptionIds"] = "b37,s23"
    mutations.append(("wrong-type-selected-ids", value))
    value = copy.deepcopy(good)
    value["selectedOptionIds"] = [[], "s23"]
    mutations.append(("unhashable-selected-id-list", value))
    value = copy.deepcopy(good)
    value["selectedOptionIds"] = [{}, "s23"]
    mutations.append(("unhashable-selected-id-object", value))
    value = copy.deepcopy(good)
    value["selectedOptionIds"] = ["b37", "b37"]
    mutations.append(("duplicate-selected-id", value))
    mutations.append(("unknown-option", enrollment({"benefit": "b99", "support": "s23"})))
    mutations.append(("cross-group-option", enrollment({"benefit": "s23", "support": "b37"})))
    value = copy.deepcopy(good)
    value["selectedOptionIds"] = ["b12", "s23"]
    mutations.append(("contradictory-final-state", value))
    value = copy.deepcopy(good)
    value["selections"][0]["commuteMode"] = TARGET
    mutations.append(("forged-answer-label", value))
    value = copy.deepcopy(good)
    value["answer"] = TARGET
    mutations.append(("extra-top-level-field", value))
    value = copy.deepcopy(good)
    value["events"] = []
    mutations.append(("missing-events", value))
    value = copy.deepcopy(good)
    value["events"][-1]["selections"] = {"benefit": "b12", "support": "s31"}
    mutations.append(("forged-submit-selections", value))
    value = copy.deepcopy(good)
    value["events"][0]["optionId"] = "b12"
    mutations.append(("contradictory-event-history", value))
    value = copy.deepcopy(good)
    value["events"].append(copy.deepcopy(value["events"][-1]))
    mutations.append(("duplicate-submit", value))
    value = copy.deepcopy(good)
    value["events"].append({"event": "select", "group": "support", "optionId": "s23"})
    mutations.append(("submit-not-last", value))
    cases.extend(spec(name, invalid, value) for name, value in mutations)
    return cases

EVIDENCE_TYPE = "constructed_verifier_fixture"


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def spec(case_id: str, category: str, artifact: object = None, *,
         expected: str = "VIOLATED", raw: str | None = None,
         missing: bool = False, observed: dict[str, str] | None = None) -> dict:
    return {
        "case_id": case_id, "category": category, "artifact": artifact,
        "raw": raw, "missing": missing, "observed": observed,
        "expected": {"verdict": expected, "reward": 1.0 if expected == "HELD" else 0.0,
                     "exit_code": 0 if expected == "HELD" else 1},
    }


def complete_case_id(selected: dict[str, str], observed: dict[str, str]) -> str:
    wrong = {group: value for group, value in observed.items() if value != TARGET}
    if not wrong:
        return "held"
    if set(observed.values()) == {"Car"}:
        return "parking"
    if len(wrong) == 1:
        group, value = next(iter(wrong.items()))
        return "single-wrong-" + group.replace("_", "-") + "-" + value.lower().replace(" ", "-")
    return "combination-" + "-".join(selected.values())


def run_cases(destination: Path, cases: list[dict] | None = None) -> dict:
    """Run real verifier subprocesses, never an agent; never overwrite evidence."""
    destination = destination.expanduser().resolve()
    repo = next((parent for parent in TASK_DIR.parents
                 if (parent / "evaluation/run_task.py").is_file()), None)
    if (repo is not None and destination.is_relative_to(repo)
            and not destination.is_relative_to(repo / "evaluation/results")):
        raise ValueError("Evidence must be outside the repository or under evaluation/results")
    cases = case_specs() if cases is None else cases
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)) or any(
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", case_id) for case_id in ids
    ):
        raise ValueError("case ids must be unique safe directory names")
    destination.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    source_hashes = {
        str(path.relative_to(TASK_DIR)): sha256(path) for path in source_paths()
    }
    metadata = {
        "schema_version": 1,
        "evidence_type": EVIDENCE_TYPE,
        "is_agent_e2e": False,
        "surface": SURFACE,
        "started_at_utc": started,
        "python_version": sys.version,
        "python_executable": sys.executable,
        "source_sha256": source_hashes,
        "check": {"dimension_id": DIMENSION, "value": TARGET, "evaluator": "rule-based"},
        "scope": "Constructed artifacts fed to the production verifier; no agent, model, GUI or browser run.",
        "expectation_basis": "Visible-option semantics independently pinned and cross-checked with the host answer key.",
        "case_categories": {
            "behavioral_complete": "Well-formed, complete selections; measures verifier discrimination.",
            "malformed_artifact": "Missing, malformed, contradictory or unsupported input; measures fail-closed handling.",
        },
    }
    write_json(destination / "metadata.json", metadata)
    records = []
    for case in cases:
        case_dir = destination / case["case_id"]
        inputs = case_dir / "input"
        verified = case_dir / "verified"
        inputs.mkdir(parents=True)
        verified.mkdir()
        artifact_path = inputs / ARTIFACT_NAME
        if not case["missing"]:
            if case["raw"] is not None:
                artifact_path.write_text(case["raw"], encoding="utf-8")
            else:
                write_json(artifact_path, case["artifact"])
        # Do not inherit credentials or ADHERENCE_* overrides from the host.
        env = {
            "PATH": os.defpath,
            "LANG": "C.UTF-8",
            "ADHERENCE_OUTPUT_DIR": str(inputs),
            "ADHERENCE_VERIFIER_DIR": str(verified),
            "ADHERENCE_TASK_DIR": str(TASK_DIR),
        }
        command = [sys.executable, str(VERIFIER)]
        try:
            process = subprocess.run(command, env=env, capture_output=True,
                                     text=True, check=False, timeout=30)
            exit_code, stdout, stderr = process.returncode, process.stdout, process.stderr
        except subprocess.TimeoutExpired:
            exit_code, stdout, stderr = None, "", "Verifier subprocess exceeded 30 seconds."
        (case_dir / "verifier.stdout.txt").write_text(stdout, encoding="utf-8")
        (case_dir / "verifier.stderr.txt").write_text(stderr, encoding="utf-8")
        parse_error = None
        try:
            structured = json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))
            reward = float((verified / "reward.txt").read_text(encoding="utf-8"))
            if not isinstance(structured, dict):
                raise ValueError("structured output is not an object")
        except (OSError, ValueError) as exc:
            structured, reward = {}, None
            parse_error = str(exc)
        actual = {"verdict": structured.get("verdict"), "reward": reward, "exit_code": exit_code}
        expected = case["expected"]
        matched = (
            actual == expected
            and structured.get("reward") == expected["reward"]
            and structured.get("passed") is (expected["verdict"] == "HELD")
            and parse_error is None
        )
        if case["observed"] is not None:
            matched = matched and structured.get("observed") == case["observed"]
        record = {
            "case_id": case["case_id"],
            "category": case["category"],
            "evidence_type": EVIDENCE_TYPE,
            "is_agent_e2e": False,
            "expected": expected,
            "expected_observed": case["observed"],
            "actual": actual,
            "matched": bool(matched),
            "artifact": None if case["missing"] else str(artifact_path.relative_to(destination)),
            "artifact_sha256": None if case["missing"] else sha256(artifact_path),
            "verifier_output": str(verified.relative_to(destination)),
            "source_metadata": "../metadata.json",
            "command": command,
            "output_parse_error": parse_error,
        }
        write_json(case_dir / "case.json", record)
        records.append(record)
    complete = [record for record in records if record["category"] == "behavioral_complete"]
    source_unchanged = source_hashes == {
        str(path.relative_to(TASK_DIR)): sha256(path) for path in source_paths()
    }
    summary = {
        "schema_version": 1,
        "evidence_type": EVIDENCE_TYPE,
        "is_agent_e2e": False,
        "surface": SURFACE,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": source_hashes,
        "total_cases": len(records),
        "matched_cases": sum(record["matched"] for record in records),
        "source_unchanged": source_unchanged,
        "all_matched": source_unchanged and all(record["matched"] for record in records),
        "behavioral_complete_cases": len(complete),
        "behavioral_expected_held": sum(record["expected"]["verdict"] == "HELD" for record in complete),
        "behavioral_actual_held": sum(record["actual"]["verdict"] == "HELD" for record in complete),
        "behavioral_actual_violated": sum(record["actual"]["verdict"] == "VIOLATED" for record in complete),
        "malformed_artifact_cases": len(records) - len(complete),
        "cases": records,
    }
    write_json(destination / "summary.json", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True,
                        help="New evidence directory; an existing destination is refused.")
    args = parser.parse_args()
    try:
        summary = run_cases(args.output_dir)
    except (FileExistsError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps({key: value for key, value in summary.items()
                      if key not in {"cases", "source_sha256"}}, indent=2))
    raise SystemExit(0 if summary["all_matched"] else 1)


if __name__ == "__main__":
    main()
