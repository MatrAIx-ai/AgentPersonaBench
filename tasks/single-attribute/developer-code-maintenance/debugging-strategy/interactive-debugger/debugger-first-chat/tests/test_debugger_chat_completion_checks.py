"""No-model fixture, budget-stop, and actual request-scope regressions."""
from __future__ import annotations

import builtins
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

_local_spec = importlib.util.spec_from_file_location(__name__ + "_completion", Path(__file__).with_name("completion_protocol.py"))
_local_completion = importlib.util.module_from_spec(_local_spec)
_local_spec.loader.exec_module(_local_completion)
_verifier_spec = importlib.util.spec_from_file_location(__name__ + "_verifier", Path(__file__).with_name("verifier.py"))
_local_verifier = importlib.util.module_from_spec(_verifier_spec)
with patch.dict(sys.modules, {"completion_protocol": _local_completion}):
    _verifier_spec.loader.exec_module(_local_verifier)
SPEC = importlib.util.spec_from_file_location("completion_calibration", Path(__file__).with_name("completion_checks.py"))
checks = importlib.util.module_from_spec(SPEC)
with patch.dict(sys.modules, {"completion_protocol": _local_completion, "verifier": _local_verifier}):
    SPEC.loader.exec_module(checks)


class Calibration(unittest.TestCase):
    def setUp(self):
        self.matrix = json.loads(Path(__file__).with_name("completion_cases.json").read_text(encoding="utf-8"))

    def test_twelve_reviewed_cases_send_no_gold_or_rationale_to_judge(self):
        cases = checks.expand_cases(self.matrix)
        self.assertEqual(len(cases), 12)
        for case in cases:
            payload = json.loads(case["payload"])
            self.assertEqual(len(payload["persona_turns"]), 12)
            self.assertNotIn("expected", payload)
            self.assertNotIn(case["rationale"], case["system_prompt"])
            self.assertNotIn(case["id"], case["payload"])
            self.assertEqual(payload["incident"], case["incident"])

    def test_unreviewed_fixture_set_cannot_freeze(self):
        self.matrix["status"] = "draft"
        with self.assertRaises(ValueError):
            checks.expand_cases(self.matrix)

    def test_transport_continuation_preserves_gold_and_total_twelve_request_cap(self):
        cases = checks.expand_cases(self.matrix)
        with tempfile.TemporaryDirectory() as temp:
            previous = Path(temp)
            checks.write(previous / "schedule.json", {"cases": cases})
            old = {"status": "failed", "attempted_calls": 1,
                   "checks": [{"id": cases[0]["id"], "error_type": "BadRequestError", "raw": None}]}
            checks.write(previous / "execution.json", old)
            remaining, meta = checks.continuation_plan(previous, cases)
            self.assertEqual(remaining, cases[1:])
            self.assertEqual(len(remaining) + meta["prior_attempted_calls"], meta["total_request_limit"])
            self.assertFalse(meta["original_twelve_case_gate_satisfied"])
            old["checks"][0]["validated_report"] = {"status": "INCOMPLETE"}
            checks.write(previous / "execution.json", old)
            with self.assertRaises(ValueError):
                checks.continuation_plan(previous, cases)

    def test_cumulative_budget_rejects_before_judge_import(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            checks.write(output / "schedule.json", {"sources": {}, "cases": checks.expand_cases(self.matrix),
                                                    "prior_attempted_calls": 1, "calibration_limit": 12})
            with self.assertRaisesRegex(ValueError, "budget"):
                checks.execute(output)
            self.assertFalse((output / "execution.json").exists())

    def test_archived_execute_rejects_current_relational_protocol_before_judge_import(self):
        original_import = builtins.__import__
        def deny_judge(name, *args, **kwargs):
            if name in {"judge", "judge_protocol", "usage"}:
                self.fail("archived driver imported a paid judge dependency")
            return original_import(name, *args, **kwargs)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            checks.write(output / "schedule.json", {"sources": {}, "cases": checks.expand_cases(self.matrix)})
            with patch("builtins.__import__", side_effect=deny_judge), self.assertRaisesRegex(
                ValueError, "archived single-judge driver"
            ):
                checks.execute(output)
            self.assertFalse((output / "execution.json").exists())

    def test_archived_freeze_rejects_current_relational_protocol_without_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "new-freeze"
            with self.assertRaisesRegex(ValueError, "archived single-judge driver"):
                checks.freeze(output)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
