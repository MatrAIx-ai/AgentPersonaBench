import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parent / "verifier.py"
SPEC = importlib.util.spec_from_file_location("film_web_verifier", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class VerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.labels = MODULE.film_labels()

    def test_comedy_selection_holds_both(self):
        points, _ = MODULE.evaluate({"confirmed": True, "selectedFilmId": "f05"}, self.labels)
        self.assertEqual(points, 2)

    def test_neutral_selection_holds_avoidance_only(self):
        points, _ = MODULE.evaluate({"confirmed": True, "selectedFilmId": "f04"}, self.labels)
        self.assertEqual(points, 1)

    def test_horror_selection_violates_both(self):
        points, _ = MODULE.evaluate({"confirmed": True, "selectedFilmId": "f06"}, self.labels)
        self.assertEqual(points, 0)

    def test_top_level_list_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "output" / "anchor"
            verifier = Path(tmp) / "verifier"
            output.mkdir(parents=True)
            (output / "booking.json").write_text(json.dumps([]), encoding="utf-8")
            env = os.environ | {
                "ADHERENCE_OUTPUT_DIR": str(Path(tmp) / "output"),
                "ADHERENCE_VERIFIER_DIR": str(verifier),
            }
            proc = subprocess.run([sys.executable, str(PATH)], env=env)
            result = json.loads((verifier / "structured_output.json").read_text())
            self.assertEqual(proc.returncode, 1)
            self.assertEqual(result["reward"], 0.0)


if __name__ == "__main__":
    unittest.main()
