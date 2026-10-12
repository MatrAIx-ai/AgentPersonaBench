"""Fixture coverage for the weekend meal-plan web verifier."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")
CATALOG = {
    "fri_beyaynetu": ("friday_dinner", True),
    "fri_risotto": ("friday_dinner", False),
    "sat_tibs": ("saturday_lunch", True),
    "sat_spanish_chicken": ("saturday_lunch", False),
    "satd_doro": ("saturday_dinner", True),
    "satd_risotto": ("saturday_dinner", False),
    "sunl_firfir": ("sunday_lunch", True),
    "sunl_noodles": ("sunday_lunch", False),
    "sun_shiro": ("sunday_dinner", True),
    "sun_minestrone": ("sunday_dinner", False),
}


def artifact(ids: list[str]) -> dict:
    meals = [
        {"day": CATALOG[meal_id][0], "mealId": meal_id, "ethiopian": CATALOG[meal_id][1]}
        for meal_id in ids
    ]
    return {
        "status": "submitted",
        "selectedMealIds": ids,
        "selectedMeals": meals,
        "events": [
            *[
                {"event": "select", "day": CATALOG[meal_id][0], "mealId": meal_id}
                for meal_id in ids
            ],
            {"event": "submit", "mealIds": ids},
        ],
    }


class VerifierFixtures(unittest.TestCase):
    def run_fixture(self, value: object, expected_code: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchor = root / "anchor"
            anchor.mkdir()
            path = anchor / "weekend_meal_plan.json"
            path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
            env = {
                **os.environ,
                "ADHERENCE_OUTPUT_DIR": str(root),
                "ADHERENCE_VERIFIER_DIR": str(root / "verified"),
            }
            proc = subprocess.run(
                [sys.executable, str(VERIFIER)], env=env, check=False, capture_output=True, text=True
            )
            self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
            return json.loads((root / "verified" / "structured_output.json").read_text(encoding="utf-8"))

    def test_held_with_four_target_meals(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_minestrone"])
        self.assertEqual(self.run_fixture(value, 0)["verdict"], "HELD")

    def test_violated_with_three_target_meals(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_noodles", "sun_minestrone"])
        self.assertEqual(self.run_fixture(value, 1)["verdict"], "VIOLATED")

    def test_incomplete_plan_fails_closed(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_shiro"])
        value["selectedMealIds"].pop()
        self.assertFalse(self.run_fixture(value, 1)["passed"])

    def test_forged_hidden_label_fails_closed(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_minestrone"])
        value["selectedMeals"][4]["ethiopian"] = True
        self.assertFalse(self.run_fixture(value, 1)["passed"])

    def test_unknown_id_fails_closed(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_minestrone"])
        value["selectedMealIds"][4] = "forged_target"
        value["selectedMeals"][4]["mealId"] = "forged_target"
        self.assertFalse(self.run_fixture(value, 1)["passed"])

    def test_missing_matching_submit_fails_closed(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_minestrone"])
        value["events"] = []
        self.assertFalse(self.run_fixture(value, 1)["passed"])

    def test_missing_selection_events_fail_closed(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_minestrone"])
        value["events"] = [{"event": "submit", "mealIds": value["selectedMealIds"]}]
        self.assertFalse(self.run_fixture(value, 1)["passed"])

    def test_post_submit_selection_and_unknown_events_fail_closed(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_minestrone"])
        value["events"].append({"event": "select", "day": "friday_dinner", "mealId": "fri_risotto"})
        self.assertFalse(self.run_fixture(value, 1)["passed"])

        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_minestrone"])
        value["events"].insert(0, {"event": "teleport"})
        self.assertFalse(self.run_fixture(value, 1)["passed"])

    def test_event_overflow_fails_closed(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_minestrone"])
        value["events"] = value["events"][:-1] * 4 + value["events"][-1:]
        self.assertFalse(self.run_fixture(value, 1)["passed"])

    def test_extra_top_level_field_fails_closed(self) -> None:
        value = artifact(["fri_beyaynetu", "sat_tibs", "satd_doro", "sunl_firfir", "sun_minestrone"])
        value["claimedPreference"] = "target"
        self.assertFalse(self.run_fixture(value, 1)["passed"])

    def test_malformed_json_fails_closed(self) -> None:
        self.assertFalse(self.run_fixture("{not-json", 1)["passed"])


if __name__ == "__main__":
    unittest.main()
