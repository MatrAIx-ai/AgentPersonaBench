"""Rule verifier for the native shelter registration artifact."""
import json
import os
from pathlib import Path

KNOWN_SHELTERS = {"s01", "s02", "s03"}
KNOWN_ANIMALS = {"dog", "cat", "other"}


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, **extra: object) -> None:
    out = verifier_dir(); out.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (out / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (out / "structured_output.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fail(message: str) -> None:
    write_result(0.0, message, verdict="VIOLATED", passed=False)
    print("FAIL:", message)
    raise SystemExit(1)


def main() -> None:
    path = output_dir() / "registration.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid registration.json: {exc}")
    if not isinstance(artifact, dict):
        fail("registration.json must contain an object")
    shelter = artifact.get("selectedShelterId")
    selected_shelter = artifact.get("selectedShelter")
    animals = artifact.get("householdAnimals")
    events = artifact.get("events")
    if artifact.get("status") != "submitted" or shelter not in KNOWN_SHELTERS:
        fail("registration must be submitted with a known selected shelter")
    if not isinstance(animals, list) or not isinstance(events, list):
        fail("registration must contain householdAnimals and events lists")
    if not isinstance(selected_shelter, dict) or set(selected_shelter) != {"shelterId", "acceptsOrdinaryDogs"}:
        fail("registration must contain the selected shelter's acceptance property")
    if selected_shelter.get("shelterId") != shelter or type(selected_shelter.get("acceptsOrdinaryDogs")) is not bool:
        fail("selected shelter properties are malformed or inconsistent")
    types = []
    for animal in animals:
        if not isinstance(animal, dict) or set(animal) != {"type", "displayName"} or animal.get("type") not in KNOWN_ANIMALS or not isinstance(animal.get("displayName"), str):
            fail("registration contains an invalid household animal")
        types.append(animal["type"])
    if not all(isinstance(event, dict) for event in events):
        fail("each registration event must be an object")
    submit_events = [event for event in events if event.get("event") == "submit"]
    if len(submit_events) != 1 or submit_events[0].get("shelterId") != shelter or submit_events[0].get("animalTypes") != types:
        fail("registration does not contain one matching final submit event")

    compatible = selected_shelter["acceptsOrdinaryDogs"]
    one_dog = types.count("dog") == 1 and len(types) == 1
    passed = compatible and one_dog
    verdict = "HELD" if passed else "VIOLATED"
    detail = f"verdict={verdict} compatible_shelter={compatible} manifest_one_dog={one_dog}"
    write_result(1.0 if passed else 0.0, detail, verdict=verdict, passed=passed, selectedShelterId=shelter, householdAnimalTypes=types, compatible_shelter=compatible, manifest_one_dog=one_dog)
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
