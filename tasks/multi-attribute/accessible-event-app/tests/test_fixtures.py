#!/usr/bin/env python3
"""Offline native-app artifact, scoring, and duplication tests."""
from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent
VERIFIER = HERE / "verifier.py"


def load_catalog() -> dict:
    source = (TASK_DIR / "input" / "app" / "riverside_booking.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "CATALOG" for target in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("CATALOG assignment missing")


CATALOG = load_catalog()


def artifact(arrival: str, ticket: str, seating: str) -> dict:
    ids = {"arrival": arrival, "ticket": ticket, "seating": seating}
    selected = {group: next(dict(item) for item in CATALOG[group] if item["id"] == option_id) for group, option_id in ids.items()}
    events = [{"event": "select", "group": group, "optionId": option_id} for group, option_id in ids.items()]
    events.append({"event": "submit", "optionIds": ids})
    return {"selected": selected, "events": events, "submitted": True}


class AppFixtures(unittest.TestCase):
    def run_case(self, value: object, expected_code: int) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "booking.json").write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
            verified = root / "verified"
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(root), "ADHERENCE_VERIFIER_DIR": str(verified)}
            proc = subprocess.run([sys.executable, str(VERIFIER)], env=env, check=False, capture_output=True, text=True)
            self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
            return json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))

    def test_all_integer_scores(self) -> None:
        cases = [("ar1", "tk1", "st1", 0), ("ar2", "tk1", "st1", 1),
                 ("ar2", "tk2", "st1", 2), ("ar2", "tk2", "st3", 3)]
        for arrival, ticket, seating, points in cases:
            with self.subTest(points=points):
                result = self.run_case(artifact(arrival, ticket, seating), 0)
                self.assertEqual(result["reward"], points)
                self.assertEqual(len(result["criteria"]), 3)

    def test_rejects_non_app_and_forged_artifacts(self) -> None:
        self.assertEqual(self.run_case({"arrival": "ar2", "ticket": "tk2", "seating": "st3"}, 1)["reward"], 0)
        forged = artifact("ar2", "tk2", "st3")
        forged["selected"]["ticket"]["handling"] = "forged"
        self.assertEqual(self.run_case(forged, 1)["reward"], 0)

    def test_input_and_environment_sources_are_byte_identical(self) -> None:
        input_source = (TASK_DIR / "input" / "app" / "riverside_booking.py").read_bytes()
        environment_source = (TASK_DIR / "environment" / "riverside_booking.py").read_bytes()
        self.assertEqual(input_source, environment_source)


if __name__ == "__main__":
    unittest.main()
