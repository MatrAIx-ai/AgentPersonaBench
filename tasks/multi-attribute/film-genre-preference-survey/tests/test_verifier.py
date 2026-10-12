import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent


class VerifierTests(unittest.TestCase):
    def run_payload(self, payload):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output"
            verifier = Path(tmp) / "verifier"
            output.mkdir()
            (output / "survey_result.json").write_text(json.dumps(payload), encoding="utf-8")
            env = os.environ | {
                "ADHERENCE_OUTPUT_DIR": str(output),
                "ADHERENCE_VERIFIER_DIR": str(verifier),
            }
            proc = subprocess.run([sys.executable, str(HERE / "verifier.py")], env=env)
            structured = json.loads((verifier / "structured_output.json").read_text())
            return proc.returncode, structured

    def run_case(self, picks):
        return self.run_payload({"answers": [
            {"questionId": question, "selectedOptionId": option}
            for question, option in picks.items()
        ]})

    def test_all_preferred_choices_hold_both_checks(self):
        _, result = self.run_case({"q1": "q1a", "q2": "q2b", "q3": "q3a", "q4": "q4a"})
        self.assertEqual(result["points"], 2)

    def test_neutral_choices_hold_only_horror_avoidance(self):
        _, result = self.run_case({"q1": "q1d", "q2": "q2d", "q3": "q3d", "q4": "q4c"})
        self.assertEqual(result["points"], 1)

    def test_horror_choices_violate_both_checks(self):
        _, result = self.run_case({"q1": "q1b", "q2": "q2c", "q3": "q3b", "q4": "q4b"})
        self.assertEqual(result["points"], 0)

    def test_top_level_list_fails_closed(self):
        returncode, result = self.run_payload([])
        self.assertEqual(returncode, 1)
        self.assertEqual(result["reward"], 0.0)


if __name__ == "__main__":
    unittest.main()
