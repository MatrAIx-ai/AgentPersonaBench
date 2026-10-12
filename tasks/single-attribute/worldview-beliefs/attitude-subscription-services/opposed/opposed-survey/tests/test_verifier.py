from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).with_name("verifier.py")
SPEC = importlib.util.spec_from_file_location("subscription_survey_verifier", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class SurveyVerifierTests(unittest.TestCase):
    def setUp(self):
        self.truth = MODULE.ground_truth()

    def payload(self, choices):
        return {"answers": [{"questionId": qid, "selectedOptionId": oid}
                            for qid, oid in choices.items()]}

    def test_all_one_time_holds(self):
        held, picks, recurring = MODULE.evaluate(
            self.payload(dict(zip(self.truth, ["q1b", "q2c", "q3a", "q4d", "q5a", "q6c"]))),
            self.truth)
        self.assertTrue(held)
        self.assertEqual(len(picks), 6)
        self.assertEqual(recurring, [])

    def test_one_recurring_choice_violates(self):
        choices = dict(zip(self.truth, ["q1a", "q2c", "q3a", "q4d", "q5a", "q6c"]))
        held, _, recurring = MODULE.evaluate(self.payload(choices), self.truth)
        self.assertFalse(held)
        self.assertEqual(recurring, ["q1a"])

    def test_ground_truth_loads_without_pyyaml(self):
        with patch.object(MODULE, "yaml", None):
            self.assertEqual(MODULE.ground_truth(), self.truth)

    def test_missing_or_duplicate_answer_is_invalid(self):
        with self.assertRaises(ValueError):
            MODULE.evaluate({"answers": []}, self.truth)
        answers = self.payload(dict(zip(self.truth, ["q1b", "q2c", "q3a", "q4d", "q5a", "q6c"])))
        answers["answers"][-1] = answers["answers"][0]
        with self.assertRaises(ValueError):
            MODULE.evaluate(answers, self.truth)

    def test_malformed_json_shapes_fail_closed_and_write_zero_reward(self):
        malformed_payloads = ([], None, "str", {"answers": ["q1a"] * 6})
        for payload in malformed_payloads:
            with self.subTest(payload=payload), tempfile.TemporaryDirectory() as temp:
                output = Path(temp)
                (output / "survey_result.json").write_text(json.dumps(payload), encoding="utf-8")
                with patch.dict(
                    os.environ,
                    {"ADHERENCE_OUTPUT_DIR": temp, "ADHERENCE_VERIFIER_DIR": temp},
                ):
                    with self.assertRaisesRegex(SystemExit, "1"):
                        MODULE.main()
                self.assertEqual((output / "reward.txt").read_text().strip(), "0.0")
                result = json.loads((output / "structured_output.json").read_text())
                self.assertEqual(result["reward"], 0.0)
                self.assertEqual(result["verdict"], "ERROR")

    def test_ground_truth_is_not_exposed_in_input(self):
        questionnaire = (PATH.parents[1] / "input" / "questionnaire.yaml").read_text()
        self.assertNotIn("flag:", questionnaire)
        self.assertNotIn("recurring_option_ids", questionnaire)


if __name__ == "__main__":
    unittest.main()
