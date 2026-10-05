#!/usr/bin/env python3
"""Fixture coverage for the dog-survey rule verifier."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")


def result(apartment: str, animals: str) -> dict:
    return {"answers": [
        {"questionId": "apartment", "selectedOptionId": apartment},
        {"questionId": "household_animals", "selectedOptionId": animals},
    ]}


class VerifierFixtures(unittest.TestCase):
    def run_fixture(self, value: object, expected_code: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "survey_result.json"
            path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(root), "ADHERENCE_VERIFIER_DIR": str(root / "verified")}
            proc = subprocess.run([sys.executable, str(VERIFIER)], env=env, check=False, capture_output=True, text=True)
            self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
            return json.loads((root / "verified" / "structured_output.json").read_text(encoding="utf-8"))

    def test_held(self) -> None:
        self.assertEqual(self.run_fixture(result("apt_linden", "animals_one_dog"), 0)["verdict"], "HELD")

    def test_violated(self) -> None:
        self.assertEqual(self.run_fixture(result("apt_harbor", "animals_none"), 1)["verdict"], "VIOLATED")

    def test_malformed(self) -> None:
        self.assertFalse(self.run_fixture("[]", 1)["passed"])


if __name__ == "__main__":
    unittest.main()
