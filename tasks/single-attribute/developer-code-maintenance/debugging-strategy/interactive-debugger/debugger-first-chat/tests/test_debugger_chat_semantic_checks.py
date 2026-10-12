"""Historical short-check fixtures remain intact but cannot rerun against construct 3."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("historical_checks", Path(__file__).with_name("semantic_checks.py"))
checks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checks)


class HistoricalChecks(unittest.TestCase):
    def test_old_number_pair_remains_unchanged(self):
        matrix = json.loads(Path(__file__).with_name("semantic_checks.json").read_text(encoding="utf-8"))
        cases = {c["id"]: c for c in matrix["checks"]}
        self.assertEqual(cases["complete_correct_expectation"]["turns"][0].replace("2160", "2000"),
                         cases["complete_wrong_expectation"]["turns"][0])

    def test_historical_execution_blocked_before_model_or_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "new"
            with self.assertRaisesRegex(ValueError, "Historical construct-2"):
                checks.freeze(output)
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError, "Historical construct-2"):
                checks.execute(output)


if __name__ == "__main__":
    unittest.main()
