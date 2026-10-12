#!/usr/bin/env python3
"""Offline fixture and opaque-key tests for accessible-event-survey."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
TASK_DIR = HERE.parent
VERIFIER = HERE / "verifier.py"


def artifact(route: str, ticket: str, seating: str) -> dict:
    return {"answers": [
        {"questionId": "arrival_route", "selectedOptionId": route},
        {"questionId": "ticket_handling", "selectedOptionId": ticket},
        {"questionId": "seating", "selectedOptionId": seating},
    ]}


class SurveyFixtures(unittest.TestCase):
    def run_case(self, value: object, expected_code: int, *, without_site_packages: bool = False) -> dict:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "survey_result.json").write_text(
                value if isinstance(value, str) else json.dumps(value), encoding="utf-8"
            )
            verified = root / "verified"
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": str(root), "ADHERENCE_VERIFIER_DIR": str(verified)}
            command = [sys.executable]
            if without_site_packages:
                command.append("-S")
            command.append(str(VERIFIER))
            proc = subprocess.run(
                command, env=env, check=False,
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, expected_code, proc.stdout + proc.stderr)
            return json.loads((verified / "structured_output.json").read_text(encoding="utf-8"))

    def test_scores_all_four_integer_outcomes(self) -> None:
        cases = [
            (artifact("r42", "t31", "s81"), 0),
            (artifact("r17", "t31", "s81"), 1),
            (artifact("r17", "t09", "s81"), 2),
            (artifact("r17", "t09", "s26"), 3),
        ]
        for value, points in cases:
            with self.subTest(points=points):
                result = self.run_case(value, 0)
                self.assertEqual(result["reward"], points)
                self.assertEqual(len(result["criteria"]), 3)

    def test_malformed_and_unknown_are_rejected(self) -> None:
        self.assertEqual(self.run_case("[]", 1)["reward"], 0)
        self.assertEqual(self.run_case(artifact("route_best", "t09", "s26"), 1)["reward"], 0)

    def test_scores_without_pyyaml(self) -> None:
        result = self.run_case(artifact("r17", "t09", "s26"), 0, without_site_packages=True)
        self.assertEqual(result["reward"], 3)
        self.assertEqual(self.run_case("[]", 1, without_site_packages=True)["reward"], 0)

    def test_questionnaire_has_opaque_ids_and_no_answer_key_fields(self) -> None:
        questionnaire = yaml.safe_load((TASK_DIR / "input" / "questionnaire.yaml").read_text(encoding="utf-8"))
        ids = [option["id"] for question in questionnaire["questions"] for option in question["options"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(len(option_id) == 3 and option_id[0].isalpha() and option_id[1:].isdigit() for option_id in ids))
        self.assertNotIn("true", (TASK_DIR / "input" / "questionnaire.yaml").read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
