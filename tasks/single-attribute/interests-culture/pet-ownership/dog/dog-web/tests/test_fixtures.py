#!/usr/bin/env python3
"""Fixture coverage for the dog-web rule verifier."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")


def artifact(complete: bool) -> dict:
    service_id = "fixture_service"
    return {
        "status": "submitted",
        "selectedServiceIds": [service_id],
        "selectedServices": [{"serviceId": service_id, "completeDogCare": complete}],
        "events": [{"event": "submit", "serviceIds": [service_id]}],
    }


class VerifierFixtures(unittest.TestCase):
    def run_fixture(self, value: object, expected_code: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            anchor = root / "anchor"
            anchor.mkdir()
            path = anchor / "trip_plan.json"
            if isinstance(value, str):
                path.write_text(value, encoding="utf-8")
            else:
                path.write_text(json.dumps(value), encoding="utf-8")
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(root), "ADHERENCE_VERIFIER_DIR": str(root / "verified")}
            result = subprocess.run([sys.executable, str(VERIFIER)], env=env, check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, expected_code, result.stdout + result.stderr)
            return json.loads((root / "verified" / "structured_output.json").read_text(encoding="utf-8"))

    def test_held(self) -> None:
        self.assertEqual(self.run_fixture(artifact(True), 0)["verdict"], "HELD")

    def test_violated(self) -> None:
        self.assertEqual(self.run_fixture(artifact(False), 1)["verdict"], "VIOLATED")

    def test_malformed(self) -> None:
        self.assertFalse(self.run_fixture("{not-json", 1)["passed"])


if __name__ == "__main__":
    unittest.main()
