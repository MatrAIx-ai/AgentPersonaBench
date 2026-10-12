"""Multi-attribute web verifier using a protected host-side answer key."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# Harbor copies tests/ into the protected verifier container. Keep scoring
# metadata and verdict mappings there, separate from agent-visible input/.
CHECKS = (
    {
        "dimension_id": "lstyle_shopping_style",
        "dimension_label": "Shopping style",
        "evaluator_name": "shopping_style=Brand loyal",
        "metric": "selected_watch_dom_label",
    },
    {
        "dimension_id": "lstyle_payment_pref",
        "dimension_label": "Payment preference",
        "evaluator_name": "payment_preference=Mobile wallet",
        "metric": "selected_payment_dom_label",
    },
    {
        "dimension_id": "att_automation",
        "dimension_label": "Attitude: Automation",
        "evaluator_name": "automation_attitude=Positive",
        "metric": "selected_setup_dom_label",
    },
)
TASK_DIR = Path(__file__).resolve().parents[1]


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, extra: dict) -> None:
    destination = verifier_dir()
    destination.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (destination / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (destination / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def fail(message: str) -> None:
    write_result(0.0, message, {
        "verdict": "VIOLATED", "passed": False, "valid_artifact": False,
        "checks": [], "score": "0/3", "points": 0, "max_points": 3,
        "passed_count": 0, "total_checks": 3,
    })
    print(f"FAIL: {message}")
    raise SystemExit(1)


def load_ground_truth() -> dict[tuple[str, str], bool]:
    if yaml is None:
        fail("pyyaml is required to read tests/answer_key.yaml")
    key_path = TASK_DIR / "tests" / "answer_key.yaml"
    if not key_path.is_file():
        fail(f"missing answer key {key_path}")
    try:
        data = yaml.safe_load(key_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        fail(f"could not parse answer key: {exc}")
    questions = data.get("questions") if isinstance(data, dict) else None
    if not isinstance(questions, dict) or not questions:
        fail("answer_key.yaml must define a non-empty questions map")

    labels = {}
    for question_id, question in questions.items():
        if not isinstance(question, dict) or not isinstance(question.get("dimension_id"), str):
            fail(f"invalid answer-key question {question_id!r}")
        options = question.get("options")
        if not isinstance(options, dict) or not options:
            fail(f"answer-key question {question_id!r} needs options")
        if not all(isinstance(option_id, str) and isinstance(held, bool)
                   for option_id, held in options.items()):
            fail(f"answer-key labels for {question_id!r} must be option-id -> bool")
        dimension_id = question["dimension_id"]
        for option_id, held in options.items():
            key = (dimension_id, option_id)
            if key in labels:
                fail(f"duplicate answer-key option {key!r}")
            labels[key] = held
    return labels


def load_selections() -> dict[str, str]:
    path = output_dir() / "anchor" / "order.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        selections = json.loads(path.read_text(encoding="utf-8")).get("selections")
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        fail(f"could not parse {path}: {exc}")
    if not isinstance(selections, list) or not selections:
        fail("order.json must contain a non-empty selections list from the DOM")
    observed = {}
    for selection in selections:
        if not isinstance(selection, dict):
            fail("every DOM selection must be an object")
        dimension_id = selection.get("dimensionId")
        option_id = selection.get("optionId")
        if not isinstance(dimension_id, str) or not isinstance(option_id, str):
            fail(f"invalid DOM selection {selection!r}")
        if dimension_id in observed:
            fail(f"duplicate DOM selection for {dimension_id!r}")
        observed[dimension_id] = option_id
    return observed


def load_generation() -> dict:
    path = output_dir() / "generation.json"
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def main() -> None:
    labels = load_ground_truth()
    selected = load_selections()
    checks = CHECKS
    expected_dimensions = {check["dimension_id"] for check in checks}
    if set(selected) != expected_dimensions:
        fail(f"DOM selections must cover exactly {sorted(expected_dimensions)}")

    results = []
    for check in checks:
        dimension_id = check["dimension_id"]
        option_id = selected[dimension_id]
        key = (dimension_id, option_id)
        if key not in labels:
            fail(f"selected DOM option is absent from the protected answer key: {key!r}")
        held = labels[key]
        results.append({
            "dimension_id": dimension_id,
            "attribute": check.get("dimension_label", check.get("attribute")),
            "evaluator": check.get("evaluator_name", dimension_id),
            "metric": check["metric"],
            "observed": option_id,
            "ground_truth_source": "tests/answer_key.yaml:option-held-label",
            "verdict": "HELD" if held else "VIOLATED",
            "passed": held,
        })

    passed_count = sum(item["passed"] for item in results)
    total = len(results)
    all_held = passed_count == total
    reward = float(passed_count)
    detail = f"score {passed_count}/{total} from DOM option IDs and protected labels"
    generation = load_generation()
    write_result(reward, detail, {
        "verdict": "HELD" if all_held else "VIOLATED",
        "passed": all_held,
        "persona": "real-human-survey-e8ec306b9cdb",
        "checks": results,
        "score": f"{passed_count}/{total}",
        "points": passed_count,
        "max_points": total,
        "passed_count": passed_count,
        "total_checks": total,
        "trajectory": generation.get("trajectory", generation.get("steps", [])),
        "generation": generation,
    })
    print(f"score={passed_count}/{total} reward={reward:.0f}")


if __name__ == "__main__":
    main()
