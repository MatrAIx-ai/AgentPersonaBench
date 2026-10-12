"""Rule-based verifier for native-app translation behavior."""
import json
import os
import tomllib
from pathlib import Path

TASK = Path(__file__).resolve().parents[1]
PERSONA = "p-08643f5024"


def output_dir():
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir():
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward, detail, payload):
    target = verifier_dir()
    target.mkdir(parents=True, exist_ok=True)
    data = {"reward": reward, "detail": detail, **payload}
    (target / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (target / "structured_output.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(message):
    write_result(0.0, message, {})
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main():
    source = output_dir() / "response.json"
    if not source.is_file():
        fail(f"missing {source}")
    try:
        artifact = json.loads(source.read_text(encoding="utf-8"))
        state = artifact.get("state")
    except (json.JSONDecodeError, AttributeError) as exc:
        fail(f"invalid response artifact: {exc}")
    if state != "submitted":
        fail("policy answer was not submitted")
    if artifact.get("selectedAnswer") not in {"answer-a", "answer-b", "answer-c"}:
        fail("policy answer selection is missing or invalid")
    events = artifact.get("events")
    if not isinstance(events, list) or not any(
            isinstance(event, dict) and event.get("event") == "submit" for event in events):
        fail("app-derived event history is missing")

    primary = artifact.get("translationUsed") is True and artifact.get("selectedLanguage") == "Spanish"
    no_english = (artifact.get("translationBeforeChoice") is True and
                  artifact.get("selectedLanguage") not in (None, "English"))
    observations = {
        "primary_language": (primary, artifact.get("selectedLanguage")),
        "english_proficiency": (no_english, artifact.get("translationBeforeChoice")),
    }
    with (TASK / "task.toml").open("rb") as handle:
        checks = tomllib.load(handle)["checks"]
    criteria = []
    for check in checks:
        held, observed = observations[check["dimension_id"]]
        criteria.append({
            "evaluator": check.get("evaluator_name", check["dimension_id"]),
            "dimension_id": check["dimension_id"], "value": check["value"],
            "observed": observed, "verdict": "HELD" if held else "VIOLATED",
            "passed": held,
        })
    points = sum(item["passed"] for item in criteria)
    total = len(criteria)
    detail = f"score {points}/{total}: " + ", ".join(
        f"{item['evaluator']}={item['verdict']}" for item in criteria)
    write_result(float(points), detail, {
        "persona": PERSONA, "criteria": criteria, "checks": criteria,
        "score": f"{points}/{total}", "points": points, "max_points": total,
        "passed_count": points, "total_checks": total, "artifact": artifact,
    })
    print(detail)


if __name__ == "__main__":
    main()
