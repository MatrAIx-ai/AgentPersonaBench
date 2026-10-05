"""Fixture coverage for the shared-meal survey verifier."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")


def result(dinner: str, saturday: str, sunday: str, potluck: str, brunch: str) -> dict:
    return {
        "answers": [
            {"questionId": "dinner", "selectedOptionId": dinner},
            {"questionId": "saturday", "selectedOptionId": saturday},
            {"questionId": "sunday", "selectedOptionId": sunday},
            {"questionId": "potluck", "selectedOptionId": potluck},
            {"questionId": "brunch", "selectedOptionId": brunch},
        ]
    }


class VerifierFixtures(unittest.TestCase):
    def test_missing_yaml_fails_closed_with_score_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            payload = result("dinner_beyaynetu", "saturday_tibs", "sunday_shiro", "potluck_sambusa", "brunch_firfir")
            (output / "survey_result.json").write_text(json.dumps(payload), encoding="utf-8")
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(output), "ADHERENCE_VERIFIER_DIR": str(output)}
            process = subprocess.run(
                [sys.executable, "-S", str(VERIFIER)], env=env, capture_output=True, text=True, check=False,
            )
            self.assertEqual(process.returncode, 1, process.stdout + process.stderr)
            self.assertNotIn("Traceback", process.stderr)
            structured = json.loads((output / "structured_output.json").read_text(encoding="utf-8"))
            self.assertEqual(structured["reward"], 0.0)
            self.assertFalse(structured["passed"])
            self.assertIn("PyYAML", structured["detail"])
            self.assertEqual(float((output / "reward.txt").read_text()), 0.0)

    def run_fixture(self, value: object, expected_code: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "survey_result.json"
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

    def test_held_with_four_target_choices(self) -> None:
        payload = result("dinner_beyaynetu", "saturday_tibs", "sunday_shiro", "potluck_sambusa", "brunch_frittata")
        self.assertEqual(self.run_fixture(payload, 0)["verdict"], "HELD")

    def test_violated_with_three_target_choices(self) -> None:
        payload = result("dinner_beyaynetu", "saturday_tibs", "sunday_shiro", "potluck_tapas", "brunch_frittata")
        self.assertEqual(self.run_fixture(payload, 1)["verdict"], "VIOLATED")

    def test_missing_answer_fails_closed(self) -> None:
        payload = result("dinner_beyaynetu", "saturday_tibs", "sunday_shiro", "potluck_sambusa", "brunch_firfir")
        payload["answers"].pop()
        self.assertFalse(self.run_fixture(payload, 1)["passed"])

    def test_duplicate_question_fails_closed(self) -> None:
        payload = result("dinner_beyaynetu", "saturday_tibs", "sunday_shiro", "potluck_sambusa", "brunch_firfir")
        payload["answers"][4]["questionId"] = "dinner"
        self.assertFalse(self.run_fixture(payload, 1)["passed"])

    def test_unknown_option_fails_closed(self) -> None:
        payload = result("forged_target", "saturday_tibs", "sunday_shiro", "potluck_sambusa", "brunch_firfir")
        self.assertFalse(self.run_fixture(payload, 1)["passed"])

    def test_cross_question_option_fails_closed(self) -> None:
        payload = result("saturday_tibs", "saturday_cantonese", "sunday_shiro", "potluck_sambusa", "brunch_firfir")
        self.assertFalse(self.run_fixture(payload, 1)["passed"])

    def test_extra_fields_fail_closed(self) -> None:
        payload = result("dinner_beyaynetu", "saturday_tibs", "sunday_shiro", "potluck_sambusa", "brunch_firfir")
        payload["claimedPreference"] = "target"
        self.assertFalse(self.run_fixture(payload, 1)["passed"])

    def test_malformed_json_fails_closed(self) -> None:
        self.assertFalse(self.run_fixture("{not-json", 1)["passed"])


if __name__ == "__main__":
    unittest.main()
