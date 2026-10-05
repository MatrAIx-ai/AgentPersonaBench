import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PATH = Path(__file__).resolve().parent / "verifier.py"
SPEC = importlib.util.spec_from_file_location("vaccine_survey_verifier", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifierTests(unittest.TestCase):
    def payload(self, ids):
        return {"answers": [
            {"questionId": f"q{i}", "selectedOptionId": oid}
            for i, oid in enumerate(ids, 1)
        ]}

    def test_all_non_vaccination_services_hold(self):
        held, hits = MODULE.evaluate(self.payload(["q1b", "q2d", "q3a", "q4c"]))
        self.assertTrue(held)
        self.assertEqual(hits, [])

    def test_one_appointment_violates(self):
        held, hits = MODULE.evaluate(self.payload(["q1b", "q2b", "q3a", "q4c"]))
        self.assertFalse(held)
        self.assertEqual(hits, ["q2b"])

    def test_incomplete_answers_rejected(self):
        with self.assertRaises(ValueError):
            MODULE.evaluate(self.payload(["q1b", "q2d"]))

    def test_wrong_top_level_types_rejected(self):
        for payload in (None, [], "text", 7):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                MODULE.evaluate(payload)

    def test_cross_question_and_wrong_option_types_rejected(self):
        bad = self.payload(["q2d", "q2d", "q3a", "q4c"])
        with self.assertRaises(ValueError):
            MODULE.evaluate(bad)

    def run_main_raw(self, raw):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "survey_result.json").write_text(raw, encoding="utf-8")
            env = {"ADHERENCE_OUTPUT_DIR": str(root),
                   "ADHERENCE_VERIFIER_DIR": str(root / "verified")}
            with patch.dict(os.environ, env), self.assertRaises(SystemExit) as stopped:
                MODULE.main()
            result = json.loads((root / "verified/structured_output.json").read_text())
            reward = (root / "verified/reward.txt").read_text().strip()
            return stopped.exception.code, reward, result

    def test_malformed_files_fail_closed_with_outputs(self):
        for raw in ("[", "null", "[]", '"text"', '{"answers":"wrong"}'):
            with self.subTest(raw=raw):
                code, reward, result = self.run_main_raw(raw)
                self.assertEqual((code, reward, result["passed"]), (1, "0.0", False))
        bad = self.payload(["q1b", "q2d", "q3a", None])
        with self.assertRaises(ValueError):
            MODULE.evaluate(bad)


if __name__ == "__main__":
    unittest.main()
