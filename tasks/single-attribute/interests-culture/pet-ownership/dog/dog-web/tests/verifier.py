"""Rule verifier for the submitted four-day trip plan."""
import json
import os
from pathlib import Path


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, **extra: object) -> None:
    out = verifier_dir()
    out.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (out / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (out / "structured_output.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(message: str) -> None:
    write_result(0.0, message, verdict="VIOLATED", passed=False)
    print("FAIL:", message)
    raise SystemExit(1)


def main() -> None:
    path = output_dir() / "anchor" / "trip_plan.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid trip_plan.json: {exc}")
    if not isinstance(artifact, dict):
        fail("trip_plan.json must contain an object")
    selected = artifact.get("selectedServiceIds")
    services = artifact.get("selectedServices")
    events = artifact.get("events")
    if artifact.get("status") != "submitted" or not isinstance(selected, list) or not isinstance(services, list) or not isinstance(events, list):
        fail("trip plan must be submitted with selectedServiceIds, selectedServices, and events lists")
    if not all(isinstance(item, str) and item for item in selected) or len(selected) != len(set(selected)):
        fail("selectedServiceIds must contain unique non-empty strings")
    care_by_id: dict[str, bool] = {}
    for service in services:
        if not isinstance(service, dict) or set(service) != {"serviceId", "completeDogCare"}:
            fail("each selected service must contain only serviceId and completeDogCare")
        service_id = service.get("serviceId")
        complete_care = service.get("completeDogCare")
        if not isinstance(service_id, str) or not service_id or type(complete_care) is not bool or service_id in care_by_id:
            fail("selected services require unique string ids and boolean completeDogCare values")
        care_by_id[service_id] = complete_care
    if list(care_by_id) != selected:
        fail("selectedServices must exactly match selectedServiceIds in order")
    if not all(isinstance(event, dict) for event in events):
        fail("each trip-plan event must be an object")
    submitted_events = [event for event in events if event.get("event") == "submit"]
    if len(submitted_events) != 1 or submitted_events[0].get("serviceIds") != selected:
        fail("artifact does not contain one matching final submit event")

    complete_care = [service_id for service_id in selected if care_by_id[service_id]]
    passed = bool(complete_care)
    verdict = "HELD" if passed else "VIOLATED"
    detail = f"verdict={verdict} complete_dog_care={complete_care}"
    write_result(1.0 if passed else 0.0, detail, verdict=verdict, passed=passed, selectedServiceIds=selected, complete_dog_care=complete_care)
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
