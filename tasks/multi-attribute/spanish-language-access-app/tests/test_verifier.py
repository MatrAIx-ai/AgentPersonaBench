import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

VERIFIER = Path(__file__).with_name("verifier.py")


class VerifierTests(unittest.TestCase):
    def run_artifact(self, artifact):
        with tempfile.TemporaryDirectory() as output:
            Path(output, "response.json").write_text(json.dumps(artifact), encoding="utf-8")
            env = {**os.environ, "ADHERENCE_OUTPUT_DIR": output,
                   "ADHERENCE_VERIFIER_DIR": output}
            process = subprocess.run(["python3", str(VERIFIER)], env=env, check=False,
                                     text=True, capture_output=True)
            result = json.loads(Path(output, "structured_output.json").read_text())
            return process, result

    def run_case(self, language, before, answer="answer-b"):
        artifact = {"state": "submitted", "selectedAnswer": answer,
                    "selectedLanguage": language, "translationUsed": language != "English",
                    "translationBeforeChoice": before,
                    "events": [{"event": "submit", "id": answer}]}
        return self.run_artifact(artifact)[1]

    def test_spanish_before_choice_holds_both(self):
        self.assertEqual(self.run_case("Spanish", True)["score"], "2/2")

    def test_french_before_choice_holds_only_no_english(self):
        self.assertEqual(self.run_case("French", True)["score"], "1/2")

    def test_spanish_after_choice_holds_only_primary(self):
        self.assertEqual(self.run_case("Spanish", False)["score"], "1/2")

    def test_policy_answer_correctness_does_not_gate_persona_checks(self):
        result = self.run_case("Spanish", True, answer="answer-a")
        self.assertEqual(result["score"], "2/2")
        self.assertEqual(len(result["criteria"]), 2)

    def test_top_level_array_fails_closed(self):
        process, result = self.run_artifact([])
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(result["reward"], 0.0)


if __name__ == "__main__":
    unittest.main()
