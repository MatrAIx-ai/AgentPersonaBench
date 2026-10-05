"""Rule verifier for the submitted five-occasion weekend meal plan."""
import json
import os
from html.parser import HTMLParser
from pathlib import Path

TASK_DIR = Path(__file__).resolve().parents[1]
EXPECTED_DAYS = ("friday_dinner", "saturday_lunch", "saturday_dinner", "sunday_lunch", "sunday_dinner")
ETHIOPIAN_CHOICES_THRESHOLD = 4


def output_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_OUTPUT_DIR", "/app/output"))


def verifier_dir() -> Path:
    return Path(os.environ.get("ADHERENCE_VERIFIER_DIR", output_dir()))


def write_result(reward: float, detail: str, **extra: object) -> None:
    out = verifier_dir()
    out.mkdir(parents=True, exist_ok=True)
    payload = {"reward": reward, "detail": detail, **extra}
    (out / "reward.txt").write_text(f"{reward}\n", encoding="utf-8")
    (out / "structured_output.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def fail(message: str) -> None:
    write_result(0.0, message, verdict="VIOLATED", passed=False)
    print("FAIL:", message)
    raise SystemExit(1)


class CatalogParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meals: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "article" and "meal" in (values.get("class") or "").split():
            self.meals.append({
                "mealId": values.get("data-id") or "",
                "day": values.get("data-day") or "",
                "ethiopian": values.get("data-ethiopian") or "",
            })


def load_catalog() -> dict[str, dict[str, object]]:
    parser = CatalogParser()
    try:
        parser.feed((TASK_DIR / "input" / "site" / "index.html").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        fail(f"could not read meal catalog: {exc}")
    catalog: dict[str, dict[str, object]] = {}
    day_counts = {day: 0 for day in EXPECTED_DAYS}
    target_counts = {day: 0 for day in EXPECTED_DAYS}
    for meal in parser.meals:
        meal_id, day, label = meal["mealId"], meal["day"], meal["ethiopian"]
        if not meal_id or meal_id in catalog or day not in day_counts or label not in {"true", "false"}:
            fail("site meal catalog has invalid, duplicate, or incomplete hidden metadata")
        catalog[meal_id] = {"day": day, "ethiopian": label == "true"}
        day_counts[day] += 1
        target_counts[day] += label == "true"
    if not catalog or any(day_counts[day] != 4 or target_counts[day] != 1 for day in EXPECTED_DAYS):
        fail("site meal catalog must contain four choices and exactly one target for each meal occasion")
    return catalog


def main() -> None:
    path = output_dir() / "anchor" / "weekend_meal_plan.json"
    if not path.is_file():
        fail(f"missing {path}")
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"invalid weekend_meal_plan.json: {exc}")
    if not isinstance(artifact, dict) or set(artifact) != {"status", "selectedMealIds", "selectedMeals", "events"}:
        fail("meal-plan artifact has an invalid top-level schema")
    if artifact["status"] != "submitted":
        fail("meal plan was not submitted")

    selected_ids = artifact["selectedMealIds"]
    selected_meals = artifact["selectedMeals"]
    events = artifact["events"]
    if not isinstance(selected_ids, list) or not isinstance(selected_meals, list) or not isinstance(events, list):
        fail("selectedMealIds, selectedMeals, and events must be lists")
    if len(selected_ids) != 5 or not all(isinstance(value, str) for value in selected_ids) or len(set(selected_ids)) != 5:
        fail("selectedMealIds must contain exactly five unique string ids")
    if len(selected_meals) != 5 or not all(isinstance(value, dict) for value in selected_meals):
        fail("selectedMeals must contain exactly five meal records")
    if not all(isinstance(event, dict) for event in events) or len(events) > 20:
        fail("events must be a bounded list of objects")

    catalog = load_catalog()
    seen_days: list[str] = []
    ethiopian_ids: list[str] = []
    for index, meal in enumerate(selected_meals):
        if set(meal) != {"day", "mealId", "ethiopian"}:
            fail("each selected meal must contain only day, mealId, and ethiopian")
        day, meal_id, label = meal["day"], meal["mealId"], meal["ethiopian"]
        if not isinstance(day, str) or not isinstance(meal_id, str) or type(label) is not bool:
            fail("selected meal fields have invalid types")
        if meal_id != selected_ids[index] or meal_id not in catalog:
            fail("selectedMeals must match selectedMealIds and use known site ids")
        expected = catalog[meal_id]
        if day != expected["day"] or label != expected["ethiopian"]:
            fail("selected meal metadata does not match the live page catalog")
        seen_days.append(day)
        if label:
            ethiopian_ids.append(meal_id)
    if tuple(seen_days) != EXPECTED_DAYS:
        fail("the submitted plan must contain one meal for each day in weekend order")

    folded: dict[str, str] = {}
    for index, event in enumerate(events):
        event_type = event.get("event")
        if event_type == "select":
            if set(event) != {"event", "day", "mealId"}:
                fail("select events must contain exactly event, day, and mealId")
            day, meal_id = event["day"], event["mealId"]
            if (
                not isinstance(day, str)
                or not isinstance(meal_id, str)
                or meal_id not in catalog
                or catalog[meal_id]["day"] != day
            ):
                fail("select event contains an unknown or cross-occasion meal")
            folded[day] = meal_id
        elif event_type == "incomplete-submit":
            if set(event) != {"event"}:
                fail("incomplete-submit events may not contain extra fields")
        elif event_type == "submit":
            if index != len(events) - 1 or set(event) != {"event", "mealIds"}:
                fail("submit must be the final event and contain only mealIds")
            if event["mealIds"] != selected_ids:
                fail("final submit event must match the selected ids")
        else:
            fail("event log contains an unknown event")
    if not events or events[-1].get("event") != "submit":
        fail("artifact must end with a submit event")
    folded_ids = [folded.get(day) for day in EXPECTED_DAYS]
    if folded_ids != selected_ids:
        fail("replayed final selections must match the submitted meal ids")

    count = len(ethiopian_ids)
    passed = count >= ETHIOPIAN_CHOICES_THRESHOLD
    verdict = "HELD" if passed else "VIOLATED"
    detail = f"verdict={verdict} ethiopian_meals={count}/5 threshold={ETHIOPIAN_CHOICES_THRESHOLD}"
    write_result(
        1.0 if passed else 0.0,
        detail,
        verdict=verdict,
        passed=passed,
        selectedMealIds=selected_ids,
        ethiopian_meal_ids=ethiopian_ids,
        ethiopian_meals=count,
        required_ethiopian_meals=ETHIOPIAN_CHOICES_THRESHOLD,
    )
    print(("PASS: " if passed else "FAIL: ") + detail)
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
