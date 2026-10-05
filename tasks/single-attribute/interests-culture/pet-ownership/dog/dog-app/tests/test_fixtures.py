#!/usr/bin/env python3
"""Fixture coverage for the dog-app rule verifier."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")


def registration(accepts: bool) -> dict:
    shelter = "fixture_shelter"
    return {
        "status": "submitted",
        "selectedShelterId": shelter,
        "selectedShelter": {"shelterId": shelter, "acceptsOrdinaryDogs": accepts},
        "householdAnimals": [{"type": "dog", "displayName": "Dog"}],
        "events": [{"event": "submit", "shelterId": shelter, "animalTypes": ["dog"]}],
    }


class VerifierFixtures(unittest.TestCase):
    def run_fixture(self, value: object, expected_code: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "registration.json"
            path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(root), "ADHERENCE_VERIFIER_DIR": str(root / "verified")}
            proc = subprocess.run([sys.executable, str(VERIFIER)], env=env, check=False, capture_output=True, text=True)
            self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
            return json.loads((root / "verified" / "structured_output.json").read_text(encoding="utf-8"))

    def test_held(self) -> None:
        held = registration(True)
        held["selectedShelterId"] = "s02"
        held["selectedShelter"]["shelterId"] = "s02"
        held["events"][0]["shelterId"] = "s02"
        self.assertEqual(self.run_fixture(held, 0)["verdict"], "HELD")

    def test_violated(self) -> None:
        violated = registration(False)
        violated["selectedShelterId"] = "s01"
        violated["selectedShelter"]["shelterId"] = "s01"
        violated["events"][0]["shelterId"] = "s01"
        self.assertEqual(self.run_fixture(violated, 1)["verdict"], "VIOLATED")

    def test_malformed(self) -> None:
        self.assertFalse(self.run_fixture("null", 1)["passed"])


if __name__ == "__main__":
    unittest.main()
